from __future__ import annotations

import json
import sqlite3

import pytest
from hermes_cli import kanban_db

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter, TaskNotFoundError
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore

from .fixtures import make_hermes_fixture


def _adapter(fixture):
    store = ReadOnlyHermesStore(
        db_path=fixture.db_path,
        board=fixture.board,
        hermes_module=kanban_db,
        log_root=fixture.log_path.parent,
    )
    return HermesReadOnlyAdapter(store)


def test_get_board_and_filtered_tasks_use_canonical_queries(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _adapter(fixture)

    board = adapter.get_board()
    tasks = adapter.list_tasks(status="review", tenant="tenant-b", limit=10)

    assert board.slug == fixture.board
    assert board.name == "Fixture Board"
    assert board.task_counts["done"] == 1
    assert [task.id for task in tasks.items] == ["review-task"]


def test_get_task_redacts_physical_paths_and_returns_canonical_detail(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    task = _adapter(fixture).get_task("review-task")

    assert task.id == "review-task"
    assert task.body == "Review body"
    assert task.latest_summary == "Review handoff"
    assert task.attachments[0].filename == "evidence.txt"
    assert "/secret/" not in json.dumps(task.model_dump())


def test_graph_contains_root_nodes_and_dependency_edges(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    graph = _adapter(fixture).get_task_graph("child-ready", depth=1)

    assert graph.root_task_id == "child-ready"
    assert {node.id for node in graph.nodes} == {"child-ready", "root"}
    assert {tuple(edge) for edge in graph.edges} == {("root", "child-ready")}


def test_activity_contains_events_runs_and_log_without_attachment_path(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    activity = _adapter(fixture).get_activity("review-task")

    assert activity.events[0].kind == "review_requested"
    assert activity.runs[0].summary == "Review handoff"
    assert "review evidence" in (activity.task_log or "")
    assert "/secret/should-not-leak.txt" not in json.dumps(activity.model_dump())


def test_unknown_task_is_a_stable_not_found_error(tmp_path):
    fixture = make_hermes_fixture(tmp_path)

    with pytest.raises(TaskNotFoundError):
        _adapter(fixture).get_task("missing")


def test_read_attachment_bytes_uses_owned_canonical_attachment_store(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    attachment_root = tmp_path / "attachments"
    attachment_path = attachment_root / "review-task" / "evidence.txt"
    attachment_path.parent.mkdir(parents=True)
    payload = b"canonical evidence\n"
    attachment_path.write_bytes(payload)
    monkeypatch.setenv("HERMES_KANBAN_ATTACHMENTS_ROOT", str(attachment_root))

    with pytest.raises(ValueError, match="not bound"):
        _adapter(fixture).read_attachment_bytes("child-ready", 1)

    with sqlite3.connect(fixture.db_path) as conn:
        conn.execute(
            "UPDATE task_attachments SET stored_path = ?, size = ? WHERE id = ?",
            (str(attachment_path), len(payload), 1),
        )
        conn.commit()

    assert _adapter(fixture).read_attachment_bytes("review-task", 1) == payload
