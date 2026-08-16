from __future__ import annotations

from enum import Enum
from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field


BoardSlug = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
TaskId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskStatus(str, Enum):
    TRIAGE = "triage"
    TODO = "todo"
    SCHEDULED = "scheduled"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


class TaskOrder(str, Enum):
    PRIORITY = "priority"
    PRIORITY_DESC = "priority-desc"
    STATUS = "status"
    ASSIGNEE = "assignee"
    TITLE = "title"
    UPDATED = "updated"


class BoardQuery(StrictModel):
    board: BoardSlug | None = None


class BoardCapabilities(StrictModel):
    read: bool
    create: bool


class BoardSummary(StrictModel):
    slug: BoardSlug
    name: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=2_000)
    project_id: str | None = Field(default=None, max_length=128)
    created_at: int | None = None
    is_default: bool
    task_counts: dict[str, int] = Field(default_factory=dict)
    capabilities: BoardCapabilities


class BoardListView(StrictModel):
    items: list[BoardSummary] = Field(max_length=50)
    default_board: BoardSlug


AssigneeName = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
TenantName = Annotated[str, Field(min_length=1, max_length=128)]
SessionId = Annotated[str, Field(min_length=1, max_length=256)]
IdempotencyKey = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")]


class CreateTaskInput(BoardQuery):
    """Strict, safe subset of Hermes' canonical create_task arguments."""

    title: str = Field(min_length=1, max_length=512)
    body: str | None = Field(default=None, max_length=64_000)
    parent_ids: list[TaskId] = Field(default_factory=list, max_length=32)
    assignee: AssigneeName | None = None
    priority: int = Field(default=0, ge=-1_000, le=1_000)
    tenant: TenantName | None = None
    session_id: SessionId | None = None
    triage: bool = False
    idempotency_key: IdempotencyKey | None = None


class ListTasksInput(BoardQuery):
    assignee: str | None = Field(default=None, max_length=128)
    status: TaskStatus | None = None
    tenant: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=256)
    include_archived: bool = False
    limit: int = Field(default=50, ge=1, le=100)
    order_by: TaskOrder = TaskOrder.PRIORITY


class TaskInput(BoardQuery):
    task_id: TaskId


class GraphInput(TaskInput):
    depth: int = Field(default=2, ge=0, le=8)
    max_nodes: int = Field(default=100, ge=1, le=500)


class ActivityInput(TaskInput):
    max_items: int = Field(default=100, ge=1, le=200)
    log_bytes: int = Field(default=16_000, ge=0, le=32_000)


class AttachmentRecord(StrictModel):
    filename: str
    content_type: str | None = None
    size: int
    uploaded_by: str | None = None
    created_at: int


class TaskSummary(StrictModel):
    id: str
    title: str
    status: str
    assignee: str | None = None
    created_by: str | None = None
    priority: int
    created_at: int
    started_at: int | None = None
    completed_at: int | None = None
    tenant: str | None = None
    session_id: str | None = None
    block_kind: str | None = None
    consecutive_failures: int = 0
    current_run_id: int | None = None
    claimed: bool = False
    result_excerpt: str | None = None


class TaskRunRecord(StrictModel):
    id: int
    status: str
    outcome: str | None = None
    profile: str | None = None
    step_key: str | None = None
    started_at: int | None = None
    ended_at: int | None = None
    summary: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class TaskEventRecord(StrictModel):
    id: int
    kind: str
    payload: Any = None
    created_at: int
    run_id: int | None = None


class TaskCommentRecord(StrictModel):
    id: int
    author: str
    body: str
    created_at: int


class BoardView(StrictModel):
    slug: str
    name: str
    description: str = ""
    task_counts: dict[str, int]
    assignee_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    oldest_ready_age_seconds: int | None = None
    generated_at: int | None = None


class TaskListView(StrictModel):
    items: list[TaskSummary]
    limit: int
    truncated: bool = False


class TaskDetail(TaskSummary):
    body: str | None = None
    workspace_kind: str | None = None
    branch_name: str | None = None
    result: str | None = None
    last_failure_error: str | None = None
    latest_summary: str | None = None
    parent_ids: list[str] = Field(default_factory=list)
    child_ids: list[str] = Field(default_factory=list)
    runs: list[TaskRunRecord] = Field(default_factory=list)
    attachments: list[AttachmentRecord] = Field(default_factory=list)
    body_truncated: bool = False


class GraphLink(StrictModel):
    id: str
    title: str
    status: str


class GraphNode(StrictModel):
    id: str
    task: TaskSummary
    parents: list[GraphLink] = Field(default_factory=list)
    children: list[GraphLink] = Field(default_factory=list)


class TaskGraphView(StrictModel):
    root_task_id: str
    nodes: list[GraphNode]
    edges: list[tuple[str, str]]
    depth: int
    truncated: bool = False


class DispatchView(StrictModel):
    task_id: str
    raw_status: str
    state: str
    reasons: list[str] = Field(default_factory=list)


class ActivityView(StrictModel):
    task_id: str
    events: list[TaskEventRecord] = Field(default_factory=list)
    comments: list[TaskCommentRecord] = Field(default_factory=list)
    runs: list[TaskRunRecord] = Field(default_factory=list)
    task_log: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    truncated: bool = False


class CreateTaskResult(StrictModel):
    created: bool
    task_id: str
    board: str
    title: str
    status: str
    assignee: str | None = None
    priority: int
    tenant: str | None = None
    session_id: str | None = None
    parent_ids: list[str] = Field(default_factory=list)
    child_ids: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at: int
