from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
from typing import Any, Iterable
from collections.abc import Callable
from pathlib import Path

from .boards import BoardHandle, BoardResolutionError, _canonical_board_slug
from .hermes import ReadOnlyHermesStore
from .schemas import (
    AddCommentResult,
    AssignTaskResult,
    CreateBoardResult,
    CreateTaskResult,
    DiagnosticsResult,
    LinkTasksResult,
    UnlinkTasksResult,
    SetModelResult,
    ReclaimResult,
    ReassignResult,
    CompleteResult,
    EditTaskResult,
    BlockResult,
    ScheduleResult,
    UnblockResult,
    RequestReviewResult,
    RequestChangesResult,
    ReopenReviewResult,
    PromoteResult,
    ArchiveResult,
)


class HermesCreateAdapter:
    """Narrow command boundary for Hermes' canonical task creation API.

    This adapter intentionally does not share the query connection or expose
    the Hermes mutation module as a general-purpose object. The only command
    reachable through this class is ``kanban_db.create_task``.
    """

    provenance = "chatgpt_mcp"

    def __init__(self, store: ReadOnlyHermesStore) -> None:
        self.store = store
        if store.hermes is None:
            raise RuntimeError("Hermes canonical module is not configured")
        self.hermes = store.hermes

    def create_task(
        self,
        *,
        title: str,
        body: str | None = None,
        parent_ids: Iterable[str] = (),
        assignee: str | None = None,
        priority: int = 0,
        tenant: str | None = None,
        session_id: str | None = None,
        triage: bool = False,
        idempotency_key: str | None = None,
    ) -> CreateTaskResult:
        if not self.store.db_path.is_file():
            raise FileNotFoundError(f"Hermes board database does not exist: {self.store.board}")
        parents = tuple(str(parent_id) for parent_id in parent_ids if str(parent_id))
        # ``connect_closing`` is Hermes' normal command connection. Passing the
        # resolved path and board keeps board selection explicit and avoids
        # mutating Hermes' active-board marker from an external request.
        with self.hermes.connect_closing(
            db_path=self.store.db_path,
            board=self.store.board,
        ) as conn:
            replay = False
            if idempotency_key:
                # Detect an idempotent replay before Hermes' canonical create
                # so the result can distinguish "new row" from "reused row".
                existing = conn.execute(
                    "SELECT id FROM tasks WHERE idempotency_key = ? AND status != 'archived' ORDER BY created_at ASC LIMIT 1",
                    (idempotency_key,),
                ).fetchone()
                replay = existing is not None
            task_id = self.hermes.create_task(
                conn,
                title=title,
                body=body,
                assignee=assignee,
                created_by=self.provenance,
                priority=priority,
                parents=parents,
                triage=triage,
                idempotency_key=idempotency_key,
                tenant=tenant,
                session_id=session_id,
                initial_status="running",
                board=self.store.board,
            )
            task = self.hermes.get_task(conn, task_id)
            if task is None:  # pragma: no cover - canonical function contract
                raise LookupError("created task could not be reloaded")
            canonical_parents = [str(value) for value in self.hermes.parent_ids(conn, task_id)]
            canonical_children = [str(value) for value in self.hermes.child_ids(conn, task_id)]

        return CreateTaskResult(
            # Hermes' idempotency contract may return an existing non-archived
            # task. The task ID is authoritative; ``created`` distinguishes a
            # fresh row from an idempotent replay.
            created=not replay,
            idempotent_replay=replay,
            task_id=str(task.id),
            board=self.store.board,
            title=str(task.title),
            status=str(task.status),
            assignee=getattr(task, "assignee", None),
            priority=int(getattr(task, "priority", 0) or 0),
            tenant=getattr(task, "tenant", None),
            session_id=getattr(task, "session_id", None),
            parent_ids=canonical_parents,
            child_ids=canonical_children,
            created_by=getattr(task, "created_by", None),
            created_at=int(getattr(task, "created_at", 0) or 0),
        )


class HermesBoardAdminAdapter:
    """Narrow boundary for canonical Hermes board creation."""

    def __init__(
        self,
        hermes: Any,
        *,
        max_board_count: int | None = None,
        active_named_board_count: Callable[[], int] | None = None,
    ) -> None:
        self.hermes = hermes
        self.max_board_count = max_board_count
        self.active_named_board_count = active_named_board_count

    @contextlib.contextmanager
    def _creation_lock(self, lock_name: str):
        """Serialize a canonical board-creation boundary across processes."""
        boards_root_factory = getattr(self.hermes, "boards_root", None)
        if not callable(boards_root_factory):
            yield
            return
        lock_root = Path(boards_root_factory()).expanduser().resolve() / ".mcp-create-locks"
        lock_root.mkdir(parents=True, exist_ok=True)
        lock_path = lock_root / lock_name
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @contextlib.contextmanager
    def _canonical_creation_lock(self, slug: str):
        """Serialize this adapter's board identity boundary across processes."""
        with self._creation_lock(f"{slug}.lock"):
            yield

    @contextlib.contextmanager
    def _quota_creation_lock(self):
        """Serialize quota discovery and canonical creation across slugs."""
        with self._creation_lock("quota.lock"):
            yield

    def _archived_slug_exists(self, slug: str) -> bool:
        boards_root_factory = getattr(self.hermes, "boards_root", None)
        if not callable(boards_root_factory):
            return False
        archive_root = Path(boards_root_factory()).expanduser().resolve() / "_archived"
        try:
            archive_root.stat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise ValueError("archived board state is unavailable") from exc
        if not archive_root.is_dir():
            raise ValueError("archived board state is unavailable")
        try:
            children = tuple(archive_root.iterdir())
        except OSError as exc:
            raise ValueError("archived board state is unavailable") from exc
        archive_name = re.compile(rf"{re.escape(slug)}-\d+(?:-\d+)?$")
        for child in children:
            if not child.is_dir():
                continue
            metadata_path = child / "board.json"
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else None
            except (OSError, ValueError):
                metadata = None
            if isinstance(metadata, dict):
                try:
                    if _canonical_board_slug(str(metadata.get("slug") or "")) == slug:
                        return True
                except ValueError:
                    pass
            if archive_name.fullmatch(child.name):
                return True
        return False

    def _existing_board(self, slug: str) -> dict[str, Any] | None:
        try:
            entries = self.hermes.list_boards(include_archived=True)
        except Exception as exc:
            raise ValueError("Hermes board discovery is unavailable") from exc
        if not isinstance(entries, list):
            raise ValueError("Hermes board discovery is unavailable")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                entry_slug = _canonical_board_slug(str(entry.get("slug") or ""))
            except ValueError:
                continue
            if entry_slug != slug:
                continue
            if bool(entry.get("archived")):
                raise ValueError("board slug is reserved by an archived board")
            return entry
        if self._archived_slug_exists(slug):
            raise ValueError("board slug is reserved by an archived board")
        return None

    @staticmethod
    def _result(metadata: dict[str, Any], *, fallback_slug: str) -> CreateBoardResult:
        result_slug = _canonical_board_slug(str(metadata.get("slug") or fallback_slug))
        return CreateBoardResult(
            slug=result_slug,
            name=str(metadata["name"]),
            description=str(metadata["description"]),
            icon=metadata.get("icon") or None,
            color=metadata.get("color") or None,
            created=True,
            is_default=result_slug == "default",
        )

    def create_board(
        self,
        slug: str,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
    ) -> CreateBoardResult:
        lookup_slug = _canonical_board_slug(slug)
        if lookup_slug == "default":
            raise ValueError("the legacy default board is reserved")
        with self._canonical_creation_lock(lookup_slug):
            quota_lock = (
                self._quota_creation_lock()
                if self.max_board_count is not None and self.active_named_board_count is not None
                else contextlib.nullcontext()
            )
            with quota_lock:
                existing = self._existing_board(lookup_slug)
                if existing is not None:
                    return self._result(existing, fallback_slug=lookup_slug)
                if self.max_board_count is not None and self.active_named_board_count is not None:
                    if self.active_named_board_count() >= self.max_board_count:
                        raise ValueError("maximum active named board count reached")
                metadata = self.hermes.create_board(
                    lookup_slug, name=name, description=description, icon=icon, color=color
                )
                return self._result(metadata, fallback_slug=lookup_slug)

    def _require_existing_board(self, slug: str) -> str:
        normalized = _canonical_board_slug(slug)
        try:
            entries = self.hermes.list_boards(include_archived=True)
        except Exception as exc:
            raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable") from exc
        for entry in entries if isinstance(entries, list) else ():
            if not isinstance(entry, dict):
                continue
            try:
                entry_slug = _canonical_board_slug(str(entry.get("slug") or ""))
            except ValueError:
                continue
            if entry_slug != normalized:
                continue
            if bool(entry.get("archived")):
                raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable")
            return normalized
        raise BoardResolutionError("BOARD_NOT_FOUND", "requested board is unavailable")

    def remove_board(self, slug: str, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ValueError("board removal requires confirm=true")
        normalized = _canonical_board_slug(slug)
        return dict(self.hermes.remove_board(normalized, archive=True))

    def switch_board(self, slug: str) -> dict[str, Any]:
        normalized = self._require_existing_board(slug)
        self.hermes.set_current_board(normalized)
        entries = self.hermes.list_boards(include_archived=False)
        return next((dict(item) for item in entries if str(item.get("slug")) == normalized), {"slug": normalized})

    def rename_board(self, slug: str, *, name: str | None = None, description: str | None = None) -> dict[str, Any]:
        normalized = self._require_existing_board(slug)
        return dict(self.hermes.write_board_metadata(normalized, name=name, description=description))

    def set_default_workdir(self, slug: str, workdir: str) -> dict[str, Any]:
        normalized = self._require_existing_board(slug)
        root = Path(workdir).expanduser().resolve()
        return dict(self.hermes.write_board_metadata(normalized, default_workdir=str(root)))


class HermesCardManagementAdapter:
    """Narrow boundary for canonical Hermes comment and assignment commands."""

    provenance = "chatgpt_mcp"

    def __init__(self, handle: BoardHandle, hermes: Any) -> None:
        self.handle = handle
        self.hermes = hermes

    def add_comment(self, task_id: str, body: str) -> AddCommentResult:
        with self.hermes.connect_closing(db_path=self.handle.db_path, board=self.handle.slug) as conn:
            comment_id = self.hermes.add_comment(conn, task_id, self.provenance, body)
            comment = next(
                (item for item in self.hermes.list_comments(conn, task_id) if item.id == comment_id),
                None,
            )
        if comment is None:
            raise RuntimeError("Hermes did not return the created comment")
        return AddCommentResult(
            board=self.handle.slug,
            task_id=str(comment.task_id),
            comment_id=int(comment.id),
            author=str(comment.author),
            created_at=int(comment.created_at),
        )

    def assign_task(self, task_id: str, assignee: str | None) -> AssignTaskResult:
        with self.hermes.connect_closing(db_path=self.handle.db_path, board=self.handle.slug) as conn:
            if not self.hermes.assign_task(conn, task_id, assignee):
                raise ValueError(f"unknown task {task_id}")
            task = self.hermes.get_task(conn, task_id)
        if task is None:
            raise RuntimeError("Hermes did not return the assigned task")
        return AssignTaskResult(
            board=self.handle.slug,
            task_id=str(task.id),
            assignee=task.assignee,
            status=str(task.status),
        )

    def _with_conn(self, callback):
        with self.hermes.connect_closing(db_path=self.handle.db_path, board=self.handle.slug) as conn:
            return callback(conn)

    def diagnostics(self, task_id: str | None = None) -> DiagnosticsResult:
        from hermes_cli import kanban_diagnostics as kd
        def op(conn):
            tasks = [self.hermes.get_task(conn, task_id)] if task_id else self.hermes.list_tasks(conn, include_archived=False, limit=1000, order_by="created")
            issues = []
            for task in tasks:
                if task is None: raise ValueError(f"unknown task {task_id}")
                values = kd.compute_task_diagnostics(task, self.hermes.list_events(conn, task.id), self.hermes.list_runs(conn, task.id), graph=self.hermes.task_graph_context(conn, task.id))
                issues.extend({"task_id": str(task.id), "severity": str(item.severity), "code": str(item.code), "message": str(item.message)} for item in values)
            return DiagnosticsResult(board=self.handle.slug, issues=issues, healthy=not issues)
        return self._with_conn(op)

    def set_model(self, task_id: str, model: str | None, provider: str | None) -> SetModelResult:
        def op(conn):
            if not self.hermes.set_model_override(conn, task_id, model, provider):
                raise ValueError(f"unknown task {task_id}")
            return SetModelResult(task_id=task_id, board=self.handle.slug, model=model, provider=provider)
        return self._with_conn(op)

    def link(self, parent_id: str, child_id: str) -> LinkTasksResult:
        def op(conn):
            self.hermes.link_tasks(conn, parent_id, child_id)
            return LinkTasksResult(parent_id=parent_id, child_id=child_id, board=self.handle.slug,
                                   parent_ids=[str(x) for x in self.hermes.parent_ids(conn, child_id)],
                                   child_ids=[str(x) for x in self.hermes.child_ids(conn, parent_id)])
        return self._with_conn(op)

    def unlink(self, parent_id: str, child_id: str) -> UnlinkTasksResult:
        def op(conn):
            self.hermes.unlink_tasks(conn, parent_id, child_id)
            return UnlinkTasksResult(parent_id=parent_id, child_id=child_id, board=self.handle.slug,
                                   parent_ids=[str(x) for x in self.hermes.parent_ids(conn, child_id)],
                                   child_ids=[str(x) for x in self.hermes.child_ids(conn, parent_id)])
        return self._with_conn(op)

    def reclaim(self, task_id: str, reason: str | None = None) -> ReclaimResult:
        def op(conn):
            if not self.hermes.reclaim_task(conn, task_id, reason=reason):
                raise ValueError(f"unknown or unreclaimable task {task_id}")
            task = self.hermes.get_task(conn, task_id)
            return ReclaimResult(task_id=task_id, board=self.handle.slug, status=str(task.status))
        return self._with_conn(op)

    def reassign(self, task_id: str, profile: str, *, reclaim: bool = False, reason: str | None = None) -> ReassignResult:
        def op(conn):
            count = 1 if self.hermes.reassign_task(conn, task_id, profile, reclaim_first=reclaim, reason=reason) else 0
            return ReassignResult(board=self.handle.slug, count=count)
        return self._with_conn(op)

    def complete(self, task_ids: Iterable[str], result: str | None = None, summary: str | None = None, metadata: dict | None = None) -> CompleteResult:
        def op(conn):
            completed, skipped = [], []
            for task_id in task_ids:
                if self.hermes.complete_task(conn, task_id, result=result, summary=summary, metadata=metadata): completed.append(task_id)
                else: skipped.append(task_id)
            return CompleteResult(board=self.handle.slug, task_ids=list(task_ids), completed=completed, skipped=skipped)
        return self._with_conn(op)

    def edit(self, task_id: str, *, result: str, summary: str | None = None, metadata: dict | None = None) -> EditTaskResult:
        def op(conn):
            if not self.hermes.edit_completed_task_result(conn, task_id, result=result, summary=summary, metadata=metadata):
                raise ValueError(f"unknown task {task_id} or task is not done")
            updated = [name for name, value in (("result", result), ("summary", summary)) if value is not None]
            return EditTaskResult(board=self.handle.slug, task_id=task_id, updated_fields=updated)
        return self._with_conn(op)

    def block(self, task_ids: Iterable[str], *, kind: str | None = None, reason: str | None = None) -> BlockResult:
        def op(conn):
            blocked, skipped = [], []
            for task_id in task_ids:
                if self.hermes.block_task(conn, task_id, kind=kind, reason=reason): blocked.append(task_id)
                else: skipped.append(task_id)
            return BlockResult(board=self.handle.slug, blocked=blocked, skipped=skipped)
        return self._with_conn(op)

    def schedule(self, task_ids: Iterable[str], reason: str | None = None) -> ScheduleResult:
        def op(conn):
            scheduled, skipped = [], []
            for task_id in task_ids:
                if self.hermes.schedule_task(conn, task_id, reason=reason): scheduled.append(task_id)
                else: skipped.append(task_id)
            return ScheduleResult(board=self.handle.slug, scheduled=scheduled, skipped=skipped)
        return self._with_conn(op)

    def unblock(self, task_ids: Iterable[str], reason: str | None = None) -> UnblockResult:
        def op(conn):
            unblocked, skipped = [], []
            for task_id in task_ids:
                if reason:
                    self.hermes.add_comment(conn, task_id, self.provenance, reason)
                if self.hermes.unblock_task(conn, task_id): unblocked.append(task_id)
                else: skipped.append(task_id)
            return UnblockResult(board=self.handle.slug, unblocked=unblocked, skipped=skipped)
        return self._with_conn(op)

    def request_review(self, task_id: str, summary: str | None = None, reviewer: str | None = None, metadata: dict | None = None, force: bool = False) -> RequestReviewResult:
        def op(conn):
            value = self.hermes.request_review(conn, task_id, summary=summary, reviewer=reviewer, metadata=metadata, force=force)
            return RequestReviewResult(board=self.handle.slug, task_ids=[task_id], moved=[task_id] if value else [])
        return self._with_conn(op)

    def request_changes(self, task_id: str, reason: str) -> RequestChangesResult:
        def op(conn):
            self.hermes.request_changes(conn, task_id, reason=reason)
            return RequestChangesResult(board=self.handle.slug, task_ids=[task_id])
        return self._with_conn(op)

    def reopen_review(self, task_ids: Iterable[str], reason: str | None = None) -> ReopenReviewResult:
        def op(conn):
            ids = list(task_ids)
            for task_id in ids:
                if reason:
                    self.hermes.add_comment(conn, task_id, self.provenance, reason)
                if not self.hermes.reopen_review_task(conn, task_id): raise ValueError(f"cannot reopen {task_id}")
            return ReopenReviewResult(board=self.handle.slug, task_ids=ids)
        return self._with_conn(op)

    def promote(self, task_id: str, reason: str | None = None, ids: Iterable[str] = (), force: bool = False, dry_run: bool = False) -> PromoteResult:
        def op(conn):
            all_ids = [task_id, *list(ids)]
            for current_id in all_ids:
                ok, _ = self.hermes.promote_task(conn, current_id, actor=self.provenance, reason=reason, force=force, dry_run=dry_run)
                if not ok: raise ValueError(f"cannot promote {task_id}")
            return PromoteResult(board=self.handle.slug, task_ids=all_ids)
        return self._with_conn(op)

    def archive(self, task_ids: Iterable[str], *, rm: bool = False) -> ArchiveResult:
        def op(conn):
            archived, skipped = [], []
            for task_id in task_ids:
                operation = self.hermes.delete_archived_task if rm else self.hermes.archive_task
                if operation(conn, task_id): archived.append(task_id)
                else: skipped.append(task_id)
            return ArchiveResult(board=self.handle.slug, archived=archived, skipped=skipped)
        return self._with_conn(op)

    def claim(self, task_id: str, *, ttl_seconds: int = 900) -> dict[str, Any]:
        def op(conn):
            task = self.hermes.claim_task(conn, task_id, ttl_seconds=ttl_seconds, claimer=self.provenance)
            if task is None:
                raise ValueError(f"cannot claim task {task_id}")
            return {"task_id": str(task.id), "status": str(task.status), "assignee": task.assignee}
        return self._with_conn(op)

    def attachments(self, task_id: str) -> list[dict[str, Any]]:
        def op(conn):
            if self.hermes.get_task(conn, task_id) is None:
                raise ValueError(f"unknown task {task_id}")
            return [
                {"id": int(item.id), "filename": str(item.filename), "content_type": item.content_type,
                 "size": int(item.size), "uploaded_by": item.uploaded_by, "created_at": int(item.created_at)}
                for item in self.hermes.list_attachments(conn, task_id)
            ]
        return self._with_conn(op)

    def attach(self, task_id: str, local_path: str, *, filename: str | None = None, content_type: str | None = None) -> dict[str, Any]:
        source = Path(local_path).expanduser().resolve()
        configured_root = os.environ.get("MCP_ATTACHMENT_STAGING_ROOT")
        safe_root = Path(configured_root).expanduser().resolve() if configured_root else (self.handle.db_path.parent / "attachments-staging").resolve()
        try:
            source.relative_to(safe_root)
        except ValueError as exc:
            raise ValueError("attachment path is outside the configured board staging root") from exc
        if not source.is_file():
            raise FileNotFoundError("attachment source is unavailable")
        max_bytes = int(os.environ.get("MCP_MAX_ATTACHMENT_BYTES", str(10 * 1024 * 1024)))
        if source.stat().st_size > max_bytes:
            raise ValueError("attachment exceeds the configured size limit")
        with source.open("rb") as stream:
            data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("attachment exceeds the configured size limit")
        import mimetypes
        stored_name = filename or source.name
        detected = content_type or mimetypes.guess_type(stored_name)[0]
        def op(conn):
            attachment_id = self.hermes.store_attachment_bytes(
                conn, task_id, stored_name, data, content_type=detected, uploaded_by=self.provenance
            )
            return {"task_id": task_id, "attachment_id": int(attachment_id), "filename": stored_name, "size": len(data)}
        return self._with_conn(op)

    def attach_rm(self, attachment_id: int) -> dict[str, Any]:
        def op(conn):
            removed = self.hermes.delete_attachment(conn, attachment_id)
            if removed is None:
                raise ValueError("attachment was not found")
            return {"attachment_id": int(attachment_id), "task_id": str(removed.task_id), "removed": True}
        return self._with_conn(op)

    def tail(self, task_id: str, *, cursor: int | None = None, limit: int = 100) -> dict[str, Any]:
        """Return one bounded page of task events after a monotonic cursor."""
        def op(conn):
            if self.hermes.get_task(conn, task_id) is None:
                raise ValueError(f"unknown task {task_id}")
            events = self.hermes.list_events(conn, task_id)
            after = int(cursor or 0)
            remaining = [event for event in events if int(event.id) > after]
            page = remaining[:limit]
            next_cursor = int(page[-1].id) if page else cursor
            return {
                "task_id": task_id,
                "cursor": next_cursor,
                "events": [
                    {"id": int(event.id), "kind": str(event.kind), "payload": event.payload,
                     "created_at": int(event.created_at), "run_id": event.run_id}
                    for event in page
                ],
                "truncated": len(remaining) > len(page),
            }
        return self._with_conn(op)

    def watch(self, *, cursor: int | None = None, task_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        """Return a bounded snapshot page; never blocks waiting for events."""
        if task_id is None:
            return {"cursor": cursor, "events": [], "truncated": False}
        return self.tail(task_id, cursor=cursor, limit=limit)

    def stats(self) -> dict[str, Any]:
        return self._with_conn(lambda conn: dict(self.hermes.board_stats(conn)))

    def assignees(self) -> list[dict[str, Any]]:
        return self._with_conn(lambda conn: list(self.hermes.known_assignees(conn)))

    def heartbeat(self, task_id: str, note: str | None = None) -> dict[str, Any]:
        ok = self._with_conn(lambda conn: self.hermes.heartbeat_worker(conn, task_id, note=note))
        if not ok:
            raise ValueError(f"cannot heartbeat task {task_id}")
        return {"task_id": task_id, "recorded": True}

    def runs(self, task_id: str, limit: int = 100) -> list[Any]:
        return list(self._with_conn(lambda conn: self.hermes.list_runs(conn, task_id)))[:limit]

    def log(self, task_id: str, limit: int = 16_000) -> dict[str, Any]:
        store = ReadOnlyHermesStore(db_path=self.handle.db_path, board=self.handle.slug, hermes_module=self.hermes)
        path = store.log_path(task_id)
        content = path.read_text(encoding="utf-8", errors="ignore") if path and path.is_file() else ""
        return {"task_id": task_id, "content": content[-limit:], "truncated": len(content) > limit}

    def specify(self, task_id: str, *, body: str | None = None, properties: dict | None = None) -> dict[str, Any]:
        title = properties.get("title") if isinstance(properties, dict) else None
        assignee = properties.get("assignee") if isinstance(properties, dict) else None
        ok = self._with_conn(lambda conn: self.hermes.specify_triage_task(conn, task_id, title=title, body=body, assignee=assignee, author=self.provenance))
        if not ok:
            raise ValueError(f"cannot specify task {task_id}")
        return {"task_id": task_id, "updated": True}

    def context(self, task_id: str) -> dict[str, Any]:
        task = self._with_conn(lambda conn: self.hermes.get_task(conn, task_id))
        if task is None:
            raise ValueError(f"unknown task {task_id}")
        return {"task_id": str(task.id), "title": str(task.title), "status": str(task.status),
                "assignee": task.assignee, "priority": int(getattr(task, "priority", 0) or 0),
                "started_at": getattr(task, "started_at", None), "current_run_id": getattr(task, "current_run_id", None),
                "claimed": bool(getattr(task, "claim_lock", None))}

    @staticmethod
    def _channel_parts(channel: str | None) -> tuple[str, str, str | None]:
        if not channel:
            raise ValueError("notification channel is required")
        parts = channel.split(":", 2)
        if len(parts) not in (2, 3) or not all(parts[:2]):
            raise ValueError("notification channel must be platform:chat_id[:thread_id]")
        return parts[0], parts[1], parts[2] or None

    def notify_subscribe(self, task_id: str, channel: str, filter: str | None = None, *, platform: str | None = None, chat_id: str | None = None, thread_id: str | None = None, delivery: str | None = None) -> dict[str, Any]:
        if platform is None or chat_id is None:
            platform, chat_id, thread_id = self._channel_parts(channel)
        channel = f"{platform}:{chat_id}" + (f":{thread_id}" if thread_id else "")
        def op(conn):
            if self.hermes.get_task(conn, task_id) is None:
                raise ValueError(f"unknown task {task_id}")
            self.hermes.add_notify_sub(conn, task_id=task_id, platform=platform, chat_id=chat_id,
                                       thread_id=thread_id, delivery_mode=delivery if delivery is not None else filter)
            return {"task_id": task_id, "channel": channel, "subscribed": True}
        return self._with_conn(op)

    def notify_list(self, limit: int = 100, task_id: str | None = None) -> list[dict[str, Any]]:
        entries = list(self._with_conn(lambda conn: self.hermes.list_notify_subs(conn)))
        if task_id is not None:
            entries = [item for item in entries if str(item.get("task_id")) == task_id]
        return [{"task_id": str(item["task_id"]), "platform": str(item["platform"]), "chat_id": str(item["chat_id"]), "thread_id": item.get("thread_id") or None, "delivery": item.get("delivery") if "delivery" in item else item.get("delivery_mode")} for item in entries[:limit]]

    def notify_unsubscribe(self, task_id: str, channel: str, *, platform: str | None = None, chat_id: str | None = None, thread_id: str | None = None) -> dict[str, Any]:
        if platform is None or chat_id is None:
            platform, chat_id, thread_id = self._channel_parts(channel)
        channel = f"{platform}:{chat_id}" + (f":{thread_id}" if thread_id else "")
        removed = self._with_conn(lambda conn: self.hermes.remove_notify_sub(
            conn, task_id=task_id, platform=platform, chat_id=chat_id, thread_id=thread_id))
        return {"task_id": task_id, "channel": channel, "unsubscribed": bool(removed)}

    def dispatch(self, *, dry_run: bool = False, max_spawn: int | None = None) -> dict[str, Any]:
        result = self._with_conn(lambda conn: self.hermes.dispatch_once(
            conn, dry_run=dry_run, max_spawn=max_spawn, board=self.handle.slug))
        return {"reclaimed": int(result.reclaimed), "promoted": int(result.promoted),
                "spawned": [list(item) for item in result.spawned], "dry_run": dry_run}

    def decompose(self, task_id: str, titles: list[str], bodies: list[str] | None = None) -> dict[str, Any]:
        children = [{"title": title, "body": (bodies[index] if bodies and index < len(bodies) else None)}
                    for index, title in enumerate(titles)]
        child_ids = self._with_conn(lambda conn: self.hermes.decompose_triage_task(
            conn, task_id, root_assignee=self.provenance, children=children, author=self.provenance))
        if child_ids is None:
            raise ValueError(f"cannot decompose task {task_id}")
        return {"task_id": task_id, "parent_id": task_id, "child_ids": [str(value) for value in child_ids]}

    def init(self) -> dict[str, Any]:
        path = self.hermes.init_db(self.handle.db_path, board=self.handle.slug)
        return {"board": self.handle.slug, "db_path": str(path), "initialized": True}

    def swarm(self, *, goal: str, workers: list[str], verifier: str, synthesizer: str, tenant: str | None = None, idempotency_key: str | None = None, priority: int = 0, created_by: str = "chatgpt_mcp") -> dict[str, Any]:
        from hermes_cli import kanban_swarm
        specs = [kanban_swarm.SwarmWorkerSpec(profile=worker, title=f"{worker}: {goal[:120]}", body=goal, priority=priority) for worker in workers]
        with self.hermes.connect_closing(db_path=self.handle.db_path, board=self.handle.slug) as conn:
            result = kanban_swarm.create_swarm(conn, goal=goal, workers=specs, verifier_assignee=verifier, synthesizer_assignee=synthesizer, tenant=tenant, created_by=created_by, priority=priority, idempotency_key=idempotency_key)
        return {"board": self.handle.slug, **result.as_dict()}

    def daemon(self, *, action: str = "status") -> dict[str, Any]:
        if action not in {"status", "snapshot"}:
            raise ValueError("daemon control is limited to bounded status or snapshot")
        snapshot = self.stats()
        return {"board": self.handle.slug, "action": action, "status": "available", "bounded": True, "running": False, "snapshot": snapshot}

    def gc(self, *, dry_run: bool = False, event_retention_days: int = 30, log_retention_days: int = 30) -> dict[str, Any]:
        if dry_run:
            return {"board": self.handle.slug, "cleaned_events": 0, "cleaned_logs": 0, "cleaned_temp": 0}
        def op(conn):
            import shutil
            root = Path(self.hermes.workspaces_root(board=self.handle.slug)).resolve()
            cleaned_temp = 0
            tasks = self.hermes.list_tasks(conn, include_archived=True, limit=10_000, order_by="created")
            for task in tasks:
                if str(getattr(task, "status", "")) != "archived" or getattr(task, "workspace_kind", None) != "scratch":
                    continue
                path = Path(getattr(task, "workspace_path", None) or (root / str(task.id))).resolve()
                try:
                    path.relative_to(root)
                except ValueError:
                    continue
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                    if not path.exists(): cleaned_temp += 1
            return {"board": self.handle.slug, "cleaned_events": int(self.hermes.gc_events(conn, older_than_seconds=event_retention_days * 86400)), "cleaned_logs": int(self.hermes.gc_worker_logs(board=self.handle.slug, older_than_seconds=log_retention_days * 86400)), "cleaned_temp": cleaned_temp}
        return self._with_conn(op)

    def repair(self) -> dict[str, Any]:
        result = self.hermes.repair_db(self.handle.db_path, board=self.handle.slug)
        return {"board": self.handle.slug, "repaired": result.status == "repaired", "issues_fixed": len(result.reindexed),
                "status": result.status, "messages": list(result.messages), "post_repair_messages": list(result.post_repair_messages),
                "backup_path": str(result.backup_path) if result.backup_path else None, "reindexed": list(result.reindexed)}
