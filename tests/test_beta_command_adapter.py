from __future__ import annotations

import concurrent.futures
import re
import threading
import time
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


def test_board_admin_rejects_reserved_legacy_default_before_canonical_mutation(tmp_path, monkeypatch):
    from hermes_cli import kanban_db

    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    adapter = HermesBoardAdminAdapter(kanban_db)
    calls: list[str] = []
    original_create_board = kanban_db.create_board

    def record_create_board(slug, **kwargs):
        calls.append(str(slug))
        return original_create_board(slug, **kwargs)

    monkeypatch.setattr(kanban_db, "create_board", record_create_board)

    with pytest.raises(ValueError, match="default"):
        adapter.create_board(" DEFAULT ")

    assert calls == []
    assert not (fixture.root / "kanban" / "boards" / "default").exists()


def test_board_admin_rejects_archived_slug_before_canonical_mutation(tmp_path, monkeypatch):
    from hermes_cli import kanban_db

    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    kanban_db.create_board("archived-board", name="Archived Board")
    archived = kanban_db.remove_board("archived-board", archive=True)
    assert archived["action"] == "archived"

    adapter = HermesBoardAdminAdapter(kanban_db)
    calls: list[str] = []
    original_create_board = kanban_db.create_board

    def record_create_board(slug, **kwargs):
        calls.append(str(slug))
        return original_create_board(slug, **kwargs)

    monkeypatch.setattr(kanban_db, "create_board", record_create_board)

    with pytest.raises(ValueError, match="archived"):
        adapter.create_board(" ARCHIVED-BOARD ")

    assert calls == []
    assert not (fixture.root / "kanban" / "boards" / "archived-board").exists()


def test_board_admin_case_variant_creation_is_one_canonical_operation(tmp_path, monkeypatch):
    from hermes_cli import kanban_db

    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    adapters = [HermesBoardAdminAdapter(kanban_db), HermesBoardAdminAdapter(kanban_db)]
    calls: list[str] = []
    calls_lock = threading.Lock()
    original_create_board = kanban_db.create_board

    def record_create_board(slug, **kwargs):
        with calls_lock:
            calls.append(str(slug))
        time.sleep(0.05)
        return original_create_board(slug, **kwargs)

    monkeypatch.setattr(kanban_db, "create_board", record_create_board)
    requests = [(adapters[0], " Case-Variant-Board "), (adapters[1], "case-variant-board")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda item: item[0].create_board(item[1]), requests))

    assert calls == ["case-variant-board"]
    assert [result.slug for result in results] == ["case-variant-board", "case-variant-board"]


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
