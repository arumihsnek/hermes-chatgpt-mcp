from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
from typing import Any, Iterable
from collections.abc import Callable
from pathlib import Path

from .boards import BoardHandle, _canonical_board_slug
from .hermes import ReadOnlyHermesStore
from .schemas import AddCommentResult, AssignTaskResult, CreateBoardResult, CreateTaskResult


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
            # task. In both cases the requested resource is now available and
            # the operation completed successfully; the task ID is authoritative.
            created=True,
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
