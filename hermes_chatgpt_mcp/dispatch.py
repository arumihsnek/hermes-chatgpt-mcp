from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class DispatchState(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class DispatchProjection:
    task_id: str
    raw_status: str
    state: DispatchState
    reasons: tuple[str, ...]


def _status(task: Any) -> str:
    return str(getattr(task, "status", ""))


def project_dispatch(
    task: Any,
    parents: Iterable[Any],
    *,
    dependency_reasons: Iterable[str] | None = None,
) -> DispatchProjection:
    status = _status(task)
    reasons: list[str] = []
    if status in {"done", "archived"}:
        return DispatchProjection(task.id, status, DispatchState.COMPLETED, ("terminal_status",))
    if status == "review":
        return DispatchProjection(task.id, status, DispatchState.REVIEW, ("awaiting_review",))

    if status == "running":
        reasons.append("already_running")
    elif status == "blocked":
        reasons.append(str(getattr(task, "block_kind", None) or "explicitly_blocked"))
    elif status == "triage":
        reasons.append("triage_requires_specification")
    elif status == "scheduled":
        reasons.append("scheduled_not_ready")
    elif status == "todo":
        reasons.append("waiting_for_dispatch")
    elif status == "ready":
        if not getattr(task, "assignee", None):
            reasons.append("unassigned")
        if getattr(task, "claim_lock", None):
            reasons.append("claimed")
    else:
        reasons.append("unsupported_status")

    if dependency_reasons is None:
        pending_parent_reasons: list[str] = []
        for parent in parents:
            parent_status = _status(parent)
            if parent_status == "archived":
                # Historical retention is not success evidence.  An explicit
                # replacement can only be accepted by the canonical Hermes
                # dependency evaluator; this projection fails closed when it
                # receives only a historical parent object.
                pending_parent_reasons.append("parent_archived_unsatisfied")
            elif parent_status == "superseded":
                pending_parent_reasons.append("superseded_without_replacement")
            elif parent_status != "done":
                pending_parent_reasons.append("dependency_not_satisfied")
        reasons.extend(pending_parent_reasons)
    else:
        reasons.extend(str(reason) for reason in dependency_reasons if reason)
    if getattr(task, "consecutive_failures", 0):
        reasons.append("consecutive_failures")
    if getattr(task, "last_failure_error", None):
        reasons.append("last_failure")

    if status == "ready" and not reasons:
        state = DispatchState.READY
    else:
        state = DispatchState.BLOCKED
    return DispatchProjection(task.id, status, state, tuple(dict.fromkeys(reasons)))

