from __future__ import annotations

from types import SimpleNamespace

from hermes_chatgpt_mcp.dispatch import DispatchState, project_dispatch


def _task(**changes):
    values = dict(
        id="task",
        title="Task",
        body=None,
        assignee="worker",
        status="ready",
        priority=1,
        created_by="test",
        created_at=1,
        claim_lock=None,
        current_run_id=None,
        consecutive_failures=0,
        last_failure_error=None,
        block_kind=None,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_dispatch_maps_terminal_and_review_states():
    assert project_dispatch(_task(status="done"), []).state is DispatchState.COMPLETED
    assert project_dispatch(_task(status="archived"), []).state is DispatchState.COMPLETED
    assert project_dispatch(_task(status="review"), []).state is DispatchState.REVIEW


def test_dispatch_reports_explicit_block_reason():
    result = project_dispatch(
        _task(status="blocked", block_kind="provider", last_failure_error="429"), []
    )

    assert result.state is DispatchState.BLOCKED
    assert "provider" in result.reasons
    assert "last_failure" in result.reasons


def test_dispatch_reports_dependency_and_assignment_gates():
    pending_parent = _task(id="parent", title="Parent", status="todo")
    dependency_result = project_dispatch(_task(status="todo"), [pending_parent])
    assert dependency_result.state is DispatchState.BLOCKED
    assert "dependency_not_satisfied" in dependency_result.reasons

    unassigned_result = project_dispatch(_task(status="ready", assignee=None), [])
    assert unassigned_result.state is DispatchState.BLOCKED
    assert "unassigned" in unassigned_result.reasons


def test_archived_parent_is_not_a_satisfied_dependency():
    archived_parent = _task(id="parent", title="Archived parent", status="archived")

    result = project_dispatch(_task(status="ready"), [archived_parent])

    assert result.state is DispatchState.BLOCKED
    assert "parent_archived_unsatisfied" in result.reasons


def test_dispatch_keeps_running_out_of_ready_projection():
    result = project_dispatch(_task(status="running"), [])

    assert result.state is DispatchState.BLOCKED
    assert "already_running" in result.reasons
