from __future__ import annotations

import re
from pathlib import Path

import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.boards import BoardHandle
from hermes_chatgpt_mcp.command import HermesBoardAdminAdapter, HermesCardManagementAdapter
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore

from .fixtures import make_hermes_fixture


def _handle(fixture) -> BoardHandle:
    return BoardHandle(
        slug=fixture.board,
        name="Fixture Board",
        description="Representative board",
        project_id=None,
        created_at=None,
        is_default=True,
        db_path=fixture.db_path,
    )


def _management_adapter(fixture, monkeypatch):
    from hermes_cli import kanban_db

    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    return HermesCardManagementAdapter(_handle(fixture), kanban_db)


def _events(fixture, task_id: str) -> list[str]:
    from hermes_cli import kanban_db

    store = ReadOnlyHermesStore(
        db_path=fixture.db_path,
        board=fixture.board,
        hermes_module=kanban_db,
        hermes_agent_root=fixture.root,
    )
    return [event.kind for event in HermesReadOnlyAdapter(store).get_activity(task_id).events]


def test_board_admin_creates_canonical_directory_without_changing_current_board(tmp_path, monkeypatch):
    from hermes_cli import kanban_db

    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    adapter = HermesBoardAdminAdapter(kanban_db)
    current_board_before = kanban_db.get_current_board()

    result = adapter.create_board(
        "second-board",
        name="Second Board",
        description="Created through the canonical adapter",
        icon="board",
        color="blue",
    )

    assert kanban_db.get_current_board() == current_board_before
    board_dir = fixture.root / "kanban" / "boards" / "second-board"
    assert result.model_dump() == {
        "slug": "second-board",
        "name": "Second Board",
        "description": "Created through the canonical adapter",
        "icon": "board",
        "color": "blue",
        "created": True,
        "is_default": False,
    }
    assert (board_dir / "board.json").is_file()
    assert (board_dir / "kanban.db").is_file()
    assert fixture.db_path.is_file()


def test_management_adapter_adds_provenance_comment_and_commented_event(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    result = _management_adapter(fixture, monkeypatch).add_comment("review-task", "Evidence recorded")

    assert result.board == fixture.board
    assert result.task_id == "review-task"
    assert result.author == "chatgpt_mcp"
    assert result.comment_id > 0
    assert "commented" in _events(fixture, "review-task")


def test_management_adapter_assigns_task_and_emits_assigned_event(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    result = _management_adapter(fixture, monkeypatch).assign_task("review-task", "Planner")

    assert result.model_dump() == {
        "board": fixture.board,
        "task_id": "review-task",
        "assignee": "planner",
        "status": "review",
    }
    assert "assigned" in _events(fixture, "review-task")


@pytest.mark.parametrize("task_id", ["missing-task", "running-task"])
def test_management_adapter_rejects_invalid_assignment_without_unrelated_writes(tmp_path, monkeypatch, task_id):
    fixture = make_hermes_fixture(tmp_path)
    if task_id == "running-task":
        from hermes_cli import kanban_db

        with kanban_db.connect_closing(db_path=fixture.db_path, board=fixture.board) as conn:
            conn.execute(
                "INSERT INTO tasks (id, title, status, claim_lock, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, "Running", "running", "claimed", 1_700_000_099),
            )
    before = _events(fixture, "review-task")

    with pytest.raises((RuntimeError, ValueError), match="unknown task|currently running"):
        _management_adapter(fixture, monkeypatch).assign_task(task_id, "Planner")

    assert _events(fixture, "review-task") == before
    assert "assigned" not in _events(fixture, task_id) if task_id == "running-task" else True


def test_command_boundary_contains_no_sql_writes_and_only_expected_canonical_mutators():
    source = Path("hermes_chatgpt_mcp/command.py").read_text(encoding="utf-8")
    resolvers = Path("hermes_chatgpt_mcp/boards.py").read_text(encoding="utf-8")

    assert re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", source, re.IGNORECASE) is None
    for name in ("create_board", "add_comment", "assign_task"):
        assert f"self.hermes.{name}" in source
    for factory in ("board_admin_adapter", "management_adapter"):
        assert f"def {factory}" in resolvers
