from __future__ import annotations

from typing import Any, Iterable

from .boards import BoardHandle
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

    def __init__(self, hermes: Any) -> None:
        self.hermes = hermes

    def create_board(
        self,
        slug: str,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
    ) -> CreateBoardResult:
        existing = next(
            (
                entry
                for entry in self.hermes.list_boards(include_archived=False)
                if isinstance(entry, dict) and str(entry.get("slug")) == slug
            ),
            None,
        )
        metadata = existing or self.hermes.create_board(
            slug, name=name, description=description, icon=icon, color=color
        )
        return CreateBoardResult(
            slug=str(metadata["slug"]),
            name=str(metadata["name"]),
            description=str(metadata["description"]),
            icon=metadata.get("icon") or None,
            color=metadata.get("color") or None,
            created=True,
            is_default=str(metadata["slug"]) == "default",
        )


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
