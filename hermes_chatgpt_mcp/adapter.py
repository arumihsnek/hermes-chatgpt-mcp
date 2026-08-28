from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .dispatch import project_dispatch
from .hermes import ReadOnlyHermesStore
from .schemas import (
    ActivityView,
    AttachmentRecord,
    BoardView,
    DispatchView,
    GraphLink,
    GraphNode,
    TaskCommentRecord,
    TaskDetail,
    TaskEventRecord,
    TaskGraphView,
    TaskListView,
    TaskRunRecord,
    TaskSummary,
)


class TaskNotFoundError(LookupError):
    """Raised when Hermes has no task with the requested ID."""


class BoardNotFoundError(LookupError):
    """Raised when the selected board database is unavailable."""


def _clip(value: Any, limit: int) -> tuple[Any, bool]:
    if value is None:
        return None, False
    text = str(value)
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def _safe_key(key: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(key))[:80]


def _safe_data(value: Any, *, depth: int = 0, budget: int = 8_000) -> Any:
    if budget <= 0:
        return "[truncated]"
    if depth > 4:
        return "[depth-limited]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in list(value.items())[:100]:
            name = str(key).lower()
            if any(word in name for word in ("password", "secret", "token", "authorization", "api_key", "stored_path", "workspace_path", "cwd", "home", "env")):
                continue
            out[_safe_key(key)] = _safe_data(item, depth=depth + 1, budget=budget // 2)
        return out
    if isinstance(value, (list, tuple)):
        return [_safe_data(item, depth=depth + 1, budget=budget // 2) for item in list(value)[:100]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str):
            return value[: min(len(value), budget)]
        return value
    return str(value)[:budget]


class HermesReadOnlyAdapter:
    """Transform canonical Hermes query results into external MCP models."""

    def __init__(
        self,
        store: ReadOnlyHermesStore,
        *,
        max_body_chars: int = 64_000,
        max_log_bytes: int = 32_000,
        max_activity_items: int = 200,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.store = store
        self.max_body_chars = max_body_chars
        self.max_log_bytes = max_log_bytes
        self.max_activity_items = max_activity_items
        self._canonical_metadata = dict(metadata) if metadata is not None else None

    @property
    def hermes(self):
        if self.store.hermes is None:
            raise RuntimeError("Hermes canonical module is not configured")
        return self.store.hermes

    def _task_summary(self, task: Any) -> TaskSummary:
        result, _ = _clip(getattr(task, "result", None), 1_000)
        return TaskSummary(
            id=str(task.id),
            title=str(task.title),
            status=str(task.status),
            assignee=getattr(task, "assignee", None),
            created_by=getattr(task, "created_by", None),
            priority=int(getattr(task, "priority", 0) or 0),
            created_at=int(getattr(task, "created_at", 0) or 0),
            started_at=getattr(task, "started_at", None),
            completed_at=getattr(task, "completed_at", None),
            tenant=getattr(task, "tenant", None),
            session_id=getattr(task, "session_id", None),
            block_kind=getattr(task, "block_kind", None),
            consecutive_failures=int(getattr(task, "consecutive_failures", 0) or 0),
            current_run_id=getattr(task, "current_run_id", None),
            claimed=bool(getattr(task, "claim_lock", None) or getattr(task, "current_run_id", None)),
            result_excerpt=result,
        )

    def _metadata(self) -> dict[str, Any]:
        if self._canonical_metadata is not None:
            return self._canonical_metadata
        path = self.store.db_path.parent / "board.json"
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    return value
            except (OSError, ValueError):
                pass
        return {"slug": self.store.board, "name": self.store.board.replace("-", " ").title(), "description": ""}

    def get_board(self) -> BoardView:
        with self.store.connect() as conn:
            stats = self.hermes.board_stats(conn)
        metadata = self._metadata()
        board_revision = self._read_ui_board_revision()
        return BoardView(
            slug=self.store.board,
            name=str(metadata.get("name") or self.store.board),
            description=str(metadata.get("description") or "")[:2_000],
            task_counts={str(k): int(v) for k, v in (stats.get("by_status") or {}).items()},
            assignee_counts={
                str(assignee): {str(status): int(count) for status, count in statuses.items()}
                for assignee, statuses in (stats.get("by_assignee") or {}).items()
            },
            oldest_ready_age_seconds=stats.get("oldest_ready_age_seconds"),
            generated_at=stats.get("now"),
            board_revision=board_revision,
        )

    def _read_ui_board_revision(self) -> int:
        """Best-effort read of the UI `board_revision` table maintained by
        UiMutationAdapter. Returns 0 when the table is absent (e.g. a fresh
        board that has never had a v2 write, or a board whose UI write is not
        enabled). A failure here must never block the read surface, and this
        helper must not open a read-write connection (which would persist a
        WAL-mode header change and break read-only tree-fingerprint tests).
        """
        if not self.store.db_path.is_file():
            return 0
        try:
            with self.store.connect() as conn:
                row = conn.execute(
                    "SELECT revision FROM board_revision WHERE board=?", (self.store.board,)
                ).fetchone()
        except Exception:  # table absent, or any read error — never block the read surface
            return 0
        return int(row[0]) if row else 0

    def list_tasks(self, *, assignee: str | None = None, status: str | None = None,
                   tenant: str | None = None, session_id: str | None = None,
                   include_archived: bool = False, limit: int = 50,
                   order_by: str = "priority") -> TaskListView:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if order_by == "created_at":
            # Convenience alias for the canonical order key.
            order_by = "created"
        with self.store.connect() as conn:
            tasks = self.hermes.list_tasks(
                conn,
                assignee=assignee,
                status=status,
                tenant=tenant,
                session_id=session_id,
                include_archived=include_archived,
                limit=limit + 1,
                order_by=order_by,
            )
        return TaskListView(items=[self._task_summary(t) for t in tasks[:limit]], limit=limit, truncated=len(tasks) > limit)

    def _get_task(self, conn: Any, task_id: str) -> Any:
        task = self.hermes.get_task(conn, task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def _run_record(self, run: Any) -> TaskRunRecord:
        return TaskRunRecord(
            id=int(run.id),
            status=str(run.status),
            outcome=getattr(run, "outcome", None),
            profile=getattr(run, "profile", None),
            step_key=getattr(run, "step_key", None),
            started_at=getattr(run, "started_at", None),
            ended_at=getattr(run, "ended_at", None),
            summary=_clip(getattr(run, "summary", None), 8_000)[0],
            error=_clip(getattr(run, "error", None), 2_000)[0],
            metadata=_safe_data(getattr(run, "metadata", None)),
        )

    def _attachment_record(self, attachment: Any) -> AttachmentRecord:
        return AttachmentRecord(
            filename=str(attachment.filename),
            content_type=getattr(attachment, "content_type", None),
            size=int(getattr(attachment, "size", 0) or 0),
            uploaded_by=getattr(attachment, "uploaded_by", None),
            created_at=int(getattr(attachment, "created_at", 0) or 0),
        )

    def get_task(self, task_id: str) -> TaskDetail:
        with self.store.connect() as conn:
            task = self._get_task(conn, task_id)
            context = self.hermes.task_graph_context(conn, task_id)
            latest_summary = self.hermes.latest_summary(conn, task_id)
            runs = self.hermes.list_runs(conn, task_id, include_active=True)
            attachments = self.hermes.list_attachments(conn, task_id)
        body, body_truncated = _clip(getattr(task, "body", None), self.max_body_chars)
        return TaskDetail(
            **self._task_summary(task).model_dump(),
            body=body,
            workspace_kind=getattr(task, "workspace_kind", None),
            branch_name=getattr(task, "branch_name", None),
            result=_clip(getattr(task, "result", None), 8_000)[0],
            last_failure_error=_clip(getattr(task, "last_failure_error", None), 2_000)[0],
            latest_summary=_clip(latest_summary, 8_000)[0],
            parent_ids=[str(item["id"]) for item in context.get("parents", [])],
            child_ids=[str(item["id"]) for item in context.get("children", [])],
            runs=[self._run_record(run) for run in runs[: self.max_activity_items]],
            attachments=[self._attachment_record(item) for item in attachments[: self.max_activity_items]],
            body_truncated=body_truncated,
        )

    def get_task_graph(self, task_id: str, *, depth: int = 2, max_nodes: int = 100) -> TaskGraphView:
        if depth < 0 or depth > 8 or max_nodes < 1 or max_nodes > 500:
            raise ValueError("graph bounds are invalid")
        nodes: dict[str, GraphNode] = {}
        edges: set[tuple[str, str]] = set()
        queue: list[tuple[str, int]] = [(task_id, 0)]
        truncated = False
        with self.store.connect() as conn:
            while queue:
                current_id, current_depth = queue.pop(0)
                if current_id in nodes:
                    continue
                if len(nodes) >= max_nodes:
                    truncated = True
                    break
                task = self._get_task(conn, current_id)
                context = self.hermes.task_graph_context(conn, current_id)
                parents = [GraphLink(id=str(item["id"]), title=str(item["title"]), status=str(item["status"])) for item in context.get("parents", [])]
                children = [GraphLink(id=str(item["id"]), title=str(item["title"]), status=str(item["status"])) for item in context.get("children", [])]
                nodes[current_id] = GraphNode(id=current_id, task=self._task_summary(task), parents=parents, children=children)
                edges.update((parent.id, current_id) for parent in parents)
                edges.update((current_id, child.id) for child in children)
                if current_depth < depth:
                    queue.extend((link.id, current_depth + 1) for link in (*parents, *children))
        visible_edges = sorted(edge for edge in edges if edge[0] in nodes and edge[1] in nodes)
        return TaskGraphView(root_task_id=task_id, nodes=list(nodes.values()), edges=visible_edges, depth=depth, truncated=truncated or bool(queue))

    def get_dispatch(self, task_id: str) -> DispatchView:
        with self.store.connect() as conn:
            task = self._get_task(conn, task_id)
            parent_ids = self.hermes.parent_ids(conn, task_id)
            parents = [self._get_task(conn, parent_id) for parent_id in parent_ids]
        projection = project_dispatch(task, parents)
        return DispatchView(
            task_id=projection.task_id,
            raw_status=projection.raw_status,
            state=projection.state.value,
            reasons=list(projection.reasons),
        )

    def _read_log(self, task_id: str, log_bytes: int) -> str | None:
        if log_bytes <= 0:
            return None
        path = self.store.log_path(task_id)
        if path is not None:
            if not path.is_file():
                return None
            with path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - min(log_bytes, self.max_log_bytes)))
                return handle.read(min(log_bytes, self.max_log_bytes)).decode("utf-8", errors="replace")
        reader = getattr(self.hermes, "read_worker_log", None)
        if reader is None:
            return None
        return reader(task_id, tail_bytes=min(log_bytes, self.max_log_bytes), board=self.store.board)

    def get_activity(self, task_id: str, *, max_items: int = 100, log_bytes: int = 16_000) -> ActivityView:
        if max_items < 1 or max_items > self.max_activity_items:
            raise ValueError("activity item bound is invalid")
        if log_bytes < 0 or log_bytes > self.max_log_bytes:
            raise ValueError("activity log bound is invalid")
        with self.store.connect() as conn:
            self._get_task(conn, task_id)
            events = self.hermes.list_events(conn, task_id)
            comments = self.hermes.list_comments(conn, task_id)
            runs = self.hermes.list_runs(conn, task_id, include_active=True)
            attachments = self.hermes.list_attachments(conn, task_id)
            latest_summary = self.hermes.latest_summary(conn, task_id)
            task = self.hermes.get_task(conn, task_id)
        events = events[:max_items]
        comments = comments[:max_items]
        runs = runs[:max_items]
        attachments = attachments[:max_items]
        return ActivityView(
            task_id=task_id,
            events=[TaskEventRecord(id=int(event.id), kind=str(event.kind), payload=_safe_data(event.payload), created_at=int(event.created_at), run_id=getattr(event, "run_id", None)) for event in events],
            comments=[TaskCommentRecord(id=int(comment.id), author=str(comment.author), body=_clip(comment.body, 8_000)[0], created_at=int(comment.created_at)) for comment in comments],
            runs=[self._run_record(run) for run in runs],
            task_log=self._read_log(task_id, log_bytes),
            evidence={
                "result": _clip(getattr(task, "result", None), 8_000)[0],
                "latest_summary": _clip(latest_summary, 8_000)[0],
                "attachments": [self._attachment_record(item).model_dump() for item in attachments],
            },
            truncated=(len(events) >= max_items or len(comments) >= max_items or len(runs) >= max_items or len(attachments) >= max_items),
        )
