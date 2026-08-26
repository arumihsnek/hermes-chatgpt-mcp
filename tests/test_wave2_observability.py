from __future__ import annotations

import pytest
from hermes_cli import kanban_db

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter, RunNotFoundError
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore

from .fixtures import make_hermes_fixture


def _adapter(fixture):
    return HermesReadOnlyAdapter(
        ReadOnlyHermesStore(
            db_path=fixture.db_path,
            board=fixture.board,
            hermes_module=kanban_db,
            log_root=fixture.log_path.parent,
        )
    )


def test_run_history_and_bounded_log_contract(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _adapter(fixture)
    run = adapter.get_run(7)
    assert run.id == 7
    history = adapter.list_runs("review-task", limit=1)
    assert [item.id for item in history.runs] == [7]
    assert history.truncated is False
    log = adapter.read_bounded_log("review-task", tail_bytes=8)
    assert log.content == "vidence"
    assert log.truncated is True
    with pytest.raises(RunNotFoundError):
        adapter.get_run(999999999)
    with pytest.raises(ValueError):
        adapter.read_bounded_log("review-task", tail_bytes=32_001)


def test_active_workers_joins_running_task_to_current_run(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    with kanban_db.connect_closing(db_path=fixture.db_path, board=fixture.board) as conn:
        conn.execute(
            "INSERT INTO tasks (id, title, assignee, status, created_at, current_run_id, session_id, tenant, branch_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("running-task", "Running worker", "worker", "running", 1_700_000_200, 8, "session-run", "tenant-run", "branch-run"),
        )
        conn.execute(
            "INSERT INTO task_runs (id, task_id, profile, status, worker_pid, claim_lock, started_at, last_heartbeat_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (8, "running-task", "worker", "running", 1234, "lock-run", 1_700_000_201, 1_700_000_202),
        )
    workers = _adapter(fixture).active_workers(limit=1)
    assert workers.workers[0].task_id == "running-task"
    assert workers.workers[0].worker_pid == 1234
    assert workers.workers[0].profile == "worker"
    assert workers.count_running >= 1


def test_runtime_status_is_bounded_and_safe(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _adapter(fixture)
    status = adapter.runtime_status()
    assert status.board == fixture.board
    assert status.running_host_total == status.running_here + status.running_other_boards
    assert status.daemon == {"status": "available", "bounded": True, "running": False}
