from __future__ import annotations

from enum import Enum
from typing import Any, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


BoardSlug = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
TaskId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
BoardMetadata = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9#][A-Za-z0-9 ._:#-]{0,127}$")]
# Display-only icon/color: permits unicode incl. emoji; blocks control chars and slashes.
BoardIcon = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f/]{1,128}$")]


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
    CREATED = "created"
    CREATED_DESC = "created-desc"
    CREATED_AT = "created_at"  # convenience alias for CREATED (mapped in the adapter)


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


class BetaBoardCapabilities(StrictModel):
    read: bool
    create: bool
    manage: bool


class GlobalCapabilities(StrictModel):
    create_board: bool


class BetaBoardSummary(StrictModel):
    slug: BoardSlug
    name: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=2_000)
    project_id: str | None = Field(default=None, max_length=128)
    created_at: int | None = None
    is_default: bool
    task_counts: dict[str, int] = Field(default_factory=dict)
    capabilities: BetaBoardCapabilities


class BetaBoardListView(StrictModel):
    items: list[BetaBoardSummary] = Field(max_length=50)
    default_board: BoardSlug
    global_capabilities: GlobalCapabilities


AssigneeName = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
TenantName = Annotated[str, Field(min_length=1, max_length=128)]
SessionId = Annotated[str, Field(min_length=1, max_length=256)]
IdempotencyKey = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")]
AttachmentId = Annotated[int, Field(ge=1)]


class CreateBoardInput(StrictModel):
    slug: BoardSlug
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=2_000)
    icon: BoardIcon | None = None
    color: BoardIcon | None = None


class CreateBoardResult(StrictModel):
    slug: BoardSlug
    name: str = Field(min_length=1, max_length=512)
    description: str = Field(max_length=2_000)
    icon: BoardIcon | None = None
    color: BoardIcon | None = None
    created: bool
    is_default: bool


class AddCommentInput(BoardQuery):
    task_id: TaskId
    body: str = Field(min_length=1, max_length=16_000)


class AddCommentResult(StrictModel):
    board: BoardSlug
    task_id: TaskId
    comment_id: int
    author: str
    created_at: int


class AssignTaskInput(BoardQuery):
    task_id: TaskId
    assignee: AssigneeName


class AssignTaskResult(StrictModel):
    board: BoardSlug
    task_id: TaskId
    assignee: AssigneeName
    status: str


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
    idempotency_key: IdempotencyKey
    # Wave-1 fields — forwarded to Hermes' canonical create_task.
    skills: list[str] | None = Field(default=None, max_length=32)
    model_override: str | None = Field(default=None, max_length=512)
    provider_override: str | None = Field(default=None, max_length=512)
    workspace_kind: str = Field(default="scratch")
    workspace_path: str | None = Field(default=None, max_length=1024)
    branch_name: str | None = Field(default=None, max_length=256)
    max_runtime_seconds: int | None = Field(default=None, ge=1)
    max_retries: int | None = Field(default=None, ge=0)
    goal_mode: bool | None = Field(default=None)
    goal_max_turns: int | None = Field(default=None, ge=1)


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
    capabilities: BetaBoardCapabilities | None = None


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
    # True when the create returned an existing task matching the same
    # idempotency_key (no new row written).
    idempotent_replay: bool = False
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


# --- Batch 1: Diagnostics, link, unlink, set_model, reclaim, reassign, complete, edit, block, schedule, unblock, request_review, request_changes, reopen_review, promote, archive ---

class DiagnosticsInput(BoardQuery):
    task_id: TaskId | None = None


class DiagnosticsResult(StrictModel):
    """Result of canonical board diagnostics."""
    board: BoardSlug
    issues: list[dict[str, Any]] = Field(default_factory=list)
    healthy: bool


class LinkTasksInput(BoardQuery):
    parent_id: TaskId
    child_id: TaskId


class LinkTasksResult(StrictModel):
    parent_id: TaskId
    child_id: TaskId
    board: BoardSlug
    parent_ids: list[TaskId]
    child_ids: list[TaskId]


class UnlinkTasksInput(BoardQuery):
    parent_id: TaskId
    child_id: TaskId


class UnlinkTasksResult(StrictModel):
    parent_id: TaskId
    child_id: TaskId
    board: BoardSlug
    parent_ids: list[TaskId]
    child_ids: list[TaskId]


class SetModelInput(BoardQuery):
    task_id: TaskId
    model: str | None = Field(default=None, max_length=512)
    provider: str | None = Field(default=None, max_length=512)


class SetModelResult(StrictModel):
    task_id: TaskId
    board: BoardSlug
    model: str | None
    provider: str | None


class ReclaimInput(BoardQuery):
    task_id: TaskId
    reason: str | None = Field(default=None, max_length=1_000)


class ReclaimResult(StrictModel):
    task_id: TaskId
    board: BoardSlug
    status: str


class ReassignInput(BoardQuery):
    task_id: TaskId
    profile: AssigneeName
    reclaim: bool = False
    reason: str | None = Field(default=None, max_length=1_000)


class ReassignResult(StrictModel):
    board: BoardSlug
    count: int


class CompleteInput(BoardQuery):
    task_ids: list[TaskId] = Field(min_length=1, max_length=32)
    result: str | None = Field(default=None, max_length=8_000)
    summary: str | None = Field(default=None, max_length=8_000)
    metadata: dict[str, Any] | None = None


class CompleteResult(StrictModel):
    board: BoardSlug
    task_ids: list[TaskId]
    completed: list[TaskId]
    skipped: list[TaskId]


class EditTaskInput(BoardQuery):
    task_id: TaskId
    result: str = Field(min_length=1, max_length=8_000)
    summary: str | None = Field(default=None, max_length=8_000)
    metadata: dict[str, Any] | None = None


class EditTaskResult(StrictModel):
    board: BoardSlug
    task_id: TaskId
    updated_fields: list[str]


class UpdateTaskInput(BoardQuery):
    task_id: TaskId
    title: str | None = Field(default=None, max_length=512)
    body: str | None = Field(default=None, max_length=64_000)
    priority: int | None = Field(default=None, ge=-1_000, le=1_000)


class UpdateTaskResult(StrictModel):
    board: BoardSlug
    task_id: TaskId
    updated_fields: list[str]


class SoftRetireEdgeInput(BoardQuery):
    parent_id: TaskId
    child_id: TaskId
    replaced_by_parent_id: TaskId
    recovery_relation_id: str = Field(min_length=1, max_length=128)
    retired_by: str | None = Field(default=None, max_length=128)
    edge_state: Literal["retired", "rebound"] = Field(default="retired")


class SoftRetireEdgeResult(StrictModel):
    board: BoardSlug
    parent_id: TaskId
    child_id: TaskId
    replaced_by_parent_id: TaskId
    recovery_relation_id: str
    retired_by: str | None
    edge_state: Literal["retired", "rebound"]
    already_retired: bool


class BlockInput(BoardQuery):
    task_ids: list[TaskId] = Field(min_length=1, max_length=32)
    kind: str | None = Field(default=None, max_length=32)
    reason: str | None = Field(default=None, max_length=1_000)


class BlockResult(StrictModel):
    board: BoardSlug
    blocked: list[TaskId]
    skipped: list[TaskId]


class ScheduleInput(BoardQuery):
    task_ids: list[TaskId] = Field(min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=1_000)


class ScheduleResult(StrictModel):
    board: BoardSlug
    scheduled: list[TaskId]
    skipped: list[TaskId]


class UnblockInput(BoardQuery):
    task_ids: list[TaskId] = Field(min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=1_000)


class UnblockResult(StrictModel):
    board: BoardSlug
    unblocked: list[TaskId]
    skipped: list[TaskId]


class RequestReviewInput(BoardQuery):
    task_id: TaskId
    summary: str | None = Field(default=None, max_length=8_000)
    reviewer: AssigneeName | None = None
    metadata: dict[str, Any] | None = None
    force: bool = False


class RequestReviewResult(StrictModel):
    board: BoardSlug
    task_ids: list[TaskId]
    moved: list[TaskId]


class RequestChangesInput(BoardQuery):
    task_id: TaskId
    reason: str = Field(min_length=1, max_length=8_000)


class RequestChangesResult(StrictModel):
    board: BoardSlug
    task_ids: list[TaskId]


class ReopenReviewInput(BoardQuery):
    task_ids: list[TaskId] = Field(min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=1_000)


class ReopenReviewResult(StrictModel):
    board: BoardSlug
    task_ids: list[TaskId]


class PromoteInput(BoardQuery):
    task_id: TaskId
    reason: str | None = Field(default=None, max_length=1_000)
    ids: list[TaskId] = Field(default_factory=list, max_length=32)
    force: bool = False
    dry_run: bool = False


class PromoteResult(StrictModel):
    board: BoardSlug
    task_ids: list[TaskId]


class ArchiveInput(BoardQuery):
    task_ids: list[TaskId] = Field(min_length=1, max_length=32)
    rm: bool = False


class ArchiveResult(StrictModel):
    board: BoardSlug
    archived: list[TaskId]
    skipped: list[TaskId]


# --- Attachment management ---

class AttachmentsInput(BoardQuery):
    task_id: TaskId
    limit: int = Field(default=100, ge=1, le=1_000)


class AttachmentInfo(StrictModel):
    id: int
    filename: str
    content_type: str | None = None
    size: int
    uploaded_by: str | None = None
    created_at: int


class AttachmentsResult(StrictModel):
    task_id: TaskId
    attachments: list[AttachmentInfo]


# --- Board management additions ---

class RemoveBoardInput(StrictModel):
    slug: BoardSlug
    confirm: bool = True


class RemoveBoardResult(StrictModel):
    slug: BoardSlug
    removed: bool
    archived: bool


class SwitchBoardInput(StrictModel):
    slug: BoardSlug


class SwitchBoardResult(StrictModel):
    slug: BoardSlug
    name: str
    description: str


class RenameBoardInput(StrictModel):
    slug: BoardSlug
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=2_000)


class RenameBoardResult(StrictModel):
    slug: BoardSlug
    name: str
    description: str


class SetDefaultWorkdirInput(StrictModel):
    slug: BoardSlug
    workdir: str


class SetDefaultWorkdirResult(StrictModel):
    slug: BoardSlug
    workdir: str


# --- Stats ---

class StatsResult(StrictModel):
    board: BoardSlug
    task_counts: dict[str, int]
    assignee_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    oldest_ready_age_seconds: int | None = None


# --- Notification subscriptions ---

class NotifySubscribeInput(BoardQuery):
    task_id: TaskId
    platform: str = Field(min_length=1, max_length=64)
    chat_id: str = Field(min_length=1, max_length=256)
    thread_id: str | None = Field(default=None, max_length=256)
    delivery: Literal["notify", "notify+wake", "wake"] | None = None


class NotifySubscribeResult(StrictModel):
    task_id: TaskId
    platform: str
    chat_id: str
    thread_id: str | None = None
    delivery: str | None = None
    subscribed: bool


class NotifyListInput(BoardQuery):
    task_id: TaskId | None = None
    limit: int = Field(default=100, ge=1, le=1_000)


class NotifySubscriptionInfo(StrictModel):
    task_id: TaskId
    platform: str
    chat_id: str
    thread_id: str | None = None
    delivery: str | None = None


class NotifyListResult(StrictModel):
    subscriptions: list[NotifySubscriptionInfo]
    count: int


class NotifyUnsubscribeInput(BoardQuery):
    task_id: TaskId
    platform: str = Field(min_length=1, max_length=64)
    chat_id: str = Field(min_length=1, max_length=256)
    thread_id: str | None = Field(default=None, max_length=256)


class NotifyUnsubscribeResult(StrictModel):
    task_id: TaskId
    platform: str
    chat_id: str
    thread_id: str | None = None
    unsubscribed: bool


# --- Worker context ---

class ContextInput(BoardQuery):
    task_id: TaskId


class ContextResult(StrictModel):
    task_id: TaskId
    title: str
    status: str
    assignee: str | None = None
    priority: int
    started_at: int | None = None
    ended_at: int | None = None
    block_kind: str | None = None
    consecutive_failures: int = 0
    result_excerpt: str | None = None
    current_run_id: int | None = None
    claimed: bool = False


# --- Task specification ---

class SpecifyInput(BoardQuery):
    task_id: TaskId
    body: str | None = Field(default=None, max_length=64_000)
    properties: dict[str, Any] | None = Field(default=None)


class SpecifyResult(StrictModel):
    task_id: TaskId
    board: BoardSlug
    updated: bool


# --- Task decomposition ---

class DecomposeInput(BoardQuery):
    task_id: TaskId
    titles: list[str] = Field(min_length=1, max_length=32)
    bodies: list[str] | None = Field(default=None, max_length=10)


class DecomposeResult(StrictModel):
    task_id: TaskId
    board: BoardSlug
    parent_id: TaskId
    child_ids: list[TaskId]


# --- Garbage collection ---

class GcResult(StrictModel):
    board: BoardSlug
    cleaned_events: int
    cleaned_logs: int
    cleaned_temp: int


class GcInput(BoardQuery):
    event_retention_days: int = Field(default=30, ge=1, le=3650)
    log_retention_days: int = Field(default=30, ge=1, le=3650)
    dry_run: bool = False


# --- Repair ---

class RepairResult(StrictModel):
    board: BoardSlug
    repaired: bool
    issues_fixed: int
    status: str
    messages: list[str] = Field(default_factory=list)
    post_repair_messages: list[str] = Field(default_factory=list)
    backup_path: str | None = None
    reindexed: list[str] = Field(default_factory=list)


class TaskLogInput(BoardQuery):
    task_id: TaskId
    limit: int = Field(default=16_000, ge=0, le=32_000)
    cursor: int | None = Field(default=None, ge=0)


class TaskLogResult(StrictModel):
    task_id: TaskId
    content: str
    next_cursor: int | None = None
    truncated: bool = False


class TaskRunsInput(BoardQuery):
    task_id: TaskId
    limit: int = Field(default=100, ge=1, le=200)


class TaskRunsResult(StrictModel):
    task_id: TaskId
    runs: list[TaskRunRecord]
    truncated: bool = False


class HeartbeatInput(BoardQuery):
    task_id: TaskId
    note: str | None = Field(default=None, max_length=2_000)


class HeartbeatResult(StrictModel):
    task_id: TaskId
    recorded: bool


class AssigneesInput(BoardQuery):
    pass


class AssigneesResult(StrictModel):
    board: BoardSlug
    assignees: list[dict[str, Any]]


class TailInput(BoardQuery):
    task_id: TaskId
    cursor: int | None = Field(default=None, ge=0)
    limit: int = Field(default=100, ge=1, le=200)


class WatchInput(BoardQuery):
    task_id: TaskId | None = None
    cursor: int | None = Field(default=None, ge=0)
    limit: int = Field(default=100, ge=1, le=200)


class CanonicalActionResult(StrictModel):
    board: BoardSlug | None = None
    action: str
    data: dict[str, Any] = Field(default_factory=dict)


class AttachRemoveInput(BoardQuery):
    attachment_id: AttachmentId


class InitInput(BoardQuery):
    pass


class SwarmInput(BoardQuery):
    goal: str = Field(min_length=1, max_length=8_000)
    workers: list[str] = Field(min_length=1, max_length=32)
    verifier: AssigneeName
    synthesizer: AssigneeName
    tenant: TenantName | None = None
    idempotency_key: IdempotencyKey | None = None
    priority: int = Field(default=0, ge=-1_000, le=1_000)
    created_by: AssigneeName = "chatgpt_mcp"


class InitResult(StrictModel):
    board: BoardSlug
    db_path: str
    initialized: bool


class SwarmResult(StrictModel):
    board: BoardSlug
    root_id: TaskId
    worker_ids: list[TaskId]
    verifier_id: TaskId
    synthesizer_id: TaskId


class DaemonResult(StrictModel):
    board: BoardSlug
    action: str
    status: str
    bounded: bool
    running: bool
    snapshot: dict[str, Any] = Field(default_factory=dict)


class DaemonInput(BoardQuery):
    action: str = Field(default="status", pattern=r"^(status|snapshot)$")


class WatchResult(StrictModel):
    board: BoardSlug
    task_id: TaskId | None = None
    cursor: int | None = None
    events: list[TaskEventRecord] = Field(default_factory=list)
    truncated: bool = False


class ClaimInput(TaskInput):
    ttl_seconds: int = Field(default=900, ge=1, le=86_400)


class AttachInput(BoardQuery):
    task_id: TaskId
    local_path: str | None = Field(default=None, min_length=1, max_length=2_000)
    content_base64: str | None = Field(default=None)
    filename: str | None = Field(default=None, min_length=1, max_length=512)
    content_type: str | None = Field(default=None, max_length=128)
    hash_algo: Literal["sha256"] | None = None
    hash_expected: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")

    @model_validator(mode='after')
    def _check_attach_input(self) -> 'AttachInput':
        if self.local_path is not None and self.content_base64 is not None:
            raise ValueError("Only one of local_path or content_base64 may be provided")
        if self.local_path is None and self.content_base64 is None:
            raise ValueError("Either local_path or content_base64 must be provided")
        if self.content_base64 is not None and self.filename is None:
            raise ValueError("filename is required when content_base64 is provided")
        return self


class DispatchInput(BoardQuery):
    dry_run: bool = False
    max_spawn: int | None = Field(default=None, ge=1, le=100)


class StreamInput(BoardQuery):
    task_id: TaskId | None = None
    cursor: int | None = Field(default=None, ge=0)
    limit: int = Field(default=100, ge=1, le=200)


class BoardAdminInput(StrictModel):
    slug: BoardSlug
    confirm: bool = False
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=2_000)
    workdir: str | None = Field(default=None, max_length=2_000)


# --- Wave-2 Runs/Workers/Observability (exact §3.2 shapes) ---
class GetRunInput(StrictModel):
    board: BoardSlug | None = None
    run_id: int = Field(ge=1)


class ListRunsInput(StrictModel):
    board: BoardSlug | None = None
    task_id: TaskId
    limit: int = Field(default=100, ge=1, le=200)
    include_active: bool = True


class ActiveWorkersInput(StrictModel):
    board: BoardSlug | None = None
    limit: int = Field(default=50, ge=1, le=100)


class BoundedLogInput(StrictModel):
    board: BoardSlug | None = None
    task_id: TaskId
    tail_bytes: int = Field(default=16_000, ge=0, le=32_000)
    cursor: int | None = Field(default=None, ge=0)


class RuntimeStatusInput(StrictModel):
    board: BoardSlug | None = None


class WorkerSnapshot(StrictModel):
    task_id: TaskId
    title: str
    status: Literal["running"] = "running"
    assignee: str | None = None
    profile: str | None = None
    current_run_id: int | None = None
    worker_pid: int | None = None
    claim_lock: str | None = None
    claim_expires: int | None = None
    last_heartbeat_at: int | None = None
    started_at: int | None = None
    session_id: str | None = None
    tenant: str | None = None
    branch_name: str | None = None


class ActiveWorkersResult(StrictModel):
    board: BoardSlug
    workers: list[WorkerSnapshot]
    count_running: int
    count_other_boards: int
    oldest_running_age_seconds: int | None = None
    generated_at: int
    truncated: bool = False


class TaskLogResult(StrictModel):
    task_id: TaskId
    content: str
    next_cursor: int | None = None
    truncated: bool = False


class TaskRunsResult(StrictModel):
    task_id: TaskId
    runs: list[TaskRunRecord]
    truncated: bool = False


class RuntimeStatusResult(StrictModel):
    board: BoardSlug
    stats: dict[str, Any]
    running_here: int
    running_other_boards: int
    running_host_total: int
    daemon: dict[str, Any] | None = None
