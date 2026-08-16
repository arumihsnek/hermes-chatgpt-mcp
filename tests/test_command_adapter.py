from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.command import HermesCreateAdapter
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.schemas import CreateTaskInput

from .fixtures import make_hermes_fixture


def _adapters(fixture, monkeypatch):
    from hermes_cli import kanban_db

    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    monkeypatch.setenv("HERMES_KANBAN_BOARD", fixture.board)
    store = ReadOnlyHermesStore(
        db_path=fixture.db_path,
        board=fixture.board,
        hermes_module=kanban_db,
        hermes_agent_root=fixture.root,
    )
    return HermesCreateAdapter(store), HermesReadOnlyAdapter(store)


def test_create_adapter_uses_canonical_semantics_and_read_adapter_can_see_task(tmp_path, monkeypatch):
    command, query = _adapters(make_hermes_fixture(tmp_path), monkeypatch)

    result = command.create_task(
        title="ChatGPT-created card",
        body="Canonical body",
        assignee="Planner",
        priority=7,
        tenant="tenant-a",
        session_id="chatgpt-session",
        idempotency_key="chatgpt-test-1",
    )

    assert result.created is True
    assert result.task_id.startswith("t_")
    assert result.board == "fixture-board"
    assert result.status == "ready"
    assert result.assignee == "planner"
    assert result.created_by == "chatgpt_mcp"
    task = query.get_task(result.task_id)
    assert task.title == "ChatGPT-created card"
    assert task.body == "Canonical body"
    assert task.status == "ready"
    assert task.parent_ids == []
    activity = query.get_activity(result.task_id, max_items=20, log_bytes=0)
    assert any(event.kind == "created" for event in activity.events)


def test_create_adapter_preserves_parent_dependency_state(tmp_path, monkeypatch):
    command, query = _adapters(make_hermes_fixture(tmp_path), monkeypatch)
    parent = command.create_task(title="Parent")
    child = command.create_task(title="Child", parent_ids=[parent.task_id])

    assert child.status == "todo"
    assert child.parent_ids == [parent.task_id]
    detail = query.get_task(child.task_id)
    assert detail.parent_ids == [parent.task_id]
    graph = query.get_task_graph(child.task_id, depth=1, max_nodes=10)
    assert (parent.task_id, child.task_id) in graph.edges


def test_invalid_parent_does_not_create_a_task(tmp_path, monkeypatch):
    command, query = _adapters(make_hermes_fixture(tmp_path), monkeypatch)
    before = {task.id for task in query.list_tasks(limit=100, include_archived=True).items}

    with pytest.raises(ValueError, match="unknown parent"):
        command.create_task(title="Should not exist", parent_ids=["missing-parent"])

    after = {task.id for task in query.list_tasks(limit=100, include_archived=True).items}
    assert after == before


def test_missing_board_fails_closed_without_initializing_a_database(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    command, _ = _adapters(fixture, monkeypatch)
    fixture.db_path.unlink()

    with pytest.raises(FileNotFoundError, match="board database"):
        command.create_task(title="must not initialize")

    assert not fixture.db_path.exists()


def test_create_schema_rejects_unknown_fields_and_excessive_payloads():
    with pytest.raises(ValidationError):
        CreateTaskInput(title="x", update_task={"title": "forbidden"})
    with pytest.raises(ValidationError):
        CreateTaskInput(title="x", body="b" * 64_001)
    with pytest.raises(ValidationError):
        CreateTaskInput(title="x", parent_ids=["bad id"])
    with pytest.raises(ValidationError):
        CreateTaskInput(title="x", priority=1_001)


def test_command_adapter_contains_no_sql_write_statement():
    from pathlib import Path

    source = Path("hermes_chatgpt_mcp/command.py").read_text(encoding="utf-8")
    assert re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", source, re.IGNORECASE) is None
