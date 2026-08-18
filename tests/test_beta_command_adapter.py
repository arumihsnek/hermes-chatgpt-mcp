from __future__ import annotations

import concurrent.futures
import json
import os
import re
import subprocess
import sys
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


def test_archive_rm_deletes_only_already_archived_tasks(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _management_adapter(fixture, monkeypatch)

    result = adapter.archive(["archived-task"], rm=True)

    assert result.archived == ["archived-task"]
    assert result.skipped == []
    with adapter.hermes.connect_closing(db_path=fixture.db_path, board=fixture.board) as conn:
        assert adapter.hermes.get_task(conn, "archived-task") is None


def test_archive_rm_does_not_downgrade_non_archived_tasks(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _management_adapter(fixture, monkeypatch)

    result = adapter.archive(["child-ready"], rm=True)

    assert result.archived == []
    assert result.skipped == ["child-ready"]


def test_batch_one_implementation_contains_no_new_raw_sql_connections():
    source = Path(__file__).parents[1].joinpath("hermes_chatgpt_mcp", "command.py").read_text()
    # One pre-existing idempotency lookup predates Batch1 and is explicitly
    # retained for replay compatibility; new management methods use canonical
    # Hermes APIs only.
    assert source.count("conn.execute") == 1


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


def _run_distinct_quota_subprocess(root: Path, gate: Path, slug: str) -> subprocess.CompletedProcess[str]:
    worker = r'''
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
gate = Path(sys.argv[2])
slug = sys.argv[3]
os.environ["HERMES_KANBAN_HOME"] = str(root)

from hermes_cli import kanban_db

from hermes_chatgpt_mcp.command import HermesBoardAdminAdapter


def active_named_board_count() -> int:
    entries = kanban_db.list_boards(include_archived=False)
    count = sum(
        1
        for entry in entries
        if isinstance(entry, dict)
        and str(entry.get("slug") or "").strip().lower() != "default"
    )
    # Force both distinct-slug processes to observe the max-1 boundary before
    # either process can enter Hermes' canonical create operation.
    time.sleep(0.35)
    return count


adapter = HermesBoardAdminAdapter(
    kanban_db,
    max_board_count=2,
    active_named_board_count=active_named_board_count,
)
original_lock = adapter._canonical_creation_lock


@contextlib.contextmanager
def gated_creation_lock(lock_slug: str):
    (gate / f"{lock_slug}.ready").touch()
    deadline = time.monotonic() + 15
    while len(tuple(gate.glob("*.ready"))) < 2:
        if time.monotonic() >= deadline:
            raise RuntimeError("distinct-slug subprocess gate timed out")
        time.sleep(0.01)
    with original_lock(lock_slug):
        yield


adapter._canonical_creation_lock = gated_creation_lock

try:
    result = adapter.create_board(slug, name=slug)
except ValueError as exc:
    print(json.dumps({"status": "conflict", "message": str(exc)}), flush=True)
else:
    print(json.dumps({"status": "ok", "slug": result.slug}), flush=True)
'''
    repo_root = Path(__file__).resolve().parents[1]
    python_path = os.pathsep.join(
        path
        for path in (str(repo_root), "/home/ubuntu/hermes-agent", os.environ.get("PYTHONPATH", ""))
        if path
    )
    return subprocess.run(
        [sys.executable, "-c", worker, str(root), str(gate), slug],
        cwd=repo_root,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": python_path, "PYTHONUNBUFFERED": "1"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_board_admin_serializes_distinct_slug_quota_boundary_across_processes(tmp_path, monkeypatch):
    from hermes_cli import kanban_db

    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    gate = tmp_path / "distinct-quota-gate"
    gate.mkdir()
    slugs = ("quota-alpha", "quota-beta")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        processes = list(
            executor.map(
                lambda slug: _run_distinct_quota_subprocess(fixture.root, gate, slug),
                slugs,
            )
        )

    for process in processes:
        assert process.returncode == 0, (
            f"subprocess failed: stdout={process.stdout!r} stderr={process.stderr!r}"
        )
    payloads = [json.loads(process.stdout.strip()) for process in processes]
    assert sorted(payload["status"] for payload in payloads) == ["conflict", "ok"]
    created_slugs = {payload["slug"] for payload in payloads if payload["status"] == "ok"}
    assert len(created_slugs) == 1

    active_named = [
        entry
        for entry in kanban_db.list_boards(include_archived=False)
        if str(entry.get("slug") or "").strip().lower() != "default"
    ]
    assert len(active_named) == 2
    assert {entry["slug"] for entry in active_named} == {fixture.board} | created_slugs


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
    import ast

    source = Path("hermes_chatgpt_mcp/command.py").read_text(encoding="utf-8")
    resolvers = Path("hermes_chatgpt_mcp/boards.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Method names such as delete_archived_task are canonical Hermes APIs and
    # must not be mistaken for embedded SQL. Inspect only SQL-bearing string
    # literals and direct conn.execute calls.
    sql_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", node.value, re.IGNORECASE)
    ]
    assert sql_literals == []
    execute_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
    ]
    assert len(execute_calls) == 1
    for name in ("create_board", "add_comment", "assign_task"):
        assert f"self.hermes.{name}" in source
    for factory in ("board_admin_adapter", "management_adapter"):
        assert f"def {factory}" in resolvers
