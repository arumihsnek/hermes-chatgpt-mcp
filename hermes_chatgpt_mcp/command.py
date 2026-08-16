from __future__ import annotations

from typing import Iterable

from .hermes import ReadOnlyHermesStore
from .schemas import CreateTaskResult


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
