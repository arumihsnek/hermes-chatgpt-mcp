from __future__ import annotations

import sqlite3

import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore

from hermes_cli import kanban_db

from .fixtures import make_hermes_fixture, tree_fingerprint


def test_connection_is_read_only_and_query_only(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    before = tree_fingerprint(fixture.root)
    store = ReadOnlyHermesStore(db_path=fixture.db_path)

    with store.connect() as conn:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM tasks").fetchone()[0] == 5
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("UPDATE tasks SET title = 'mutated' WHERE id = 'root'")

    assert tree_fingerprint(fixture.root) == before


def test_all_query_adapter_reads_preserve_the_fixture_fingerprint(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    adapter = HermesReadOnlyAdapter(
        ReadOnlyHermesStore(
            db_path=fixture.db_path,
            board=fixture.board,
            hermes_module=kanban_db,
            log_root=fixture.log_path.parent,
        )
    )
    reads = (
        lambda: adapter.get_board(),
        lambda: adapter.list_tasks(include_archived=True, limit=20),
        lambda: adapter.get_task("review-task"),
        lambda: adapter.get_task_graph("child-ready", depth=1, max_nodes=10),
        lambda: adapter.get_dispatch("child-blocked"),
        lambda: adapter.get_activity("review-task", max_items=20, log_bytes=1_000),
    )

    for read in reads:
        read()
    before = tree_fingerprint(fixture.root)
    for read in reads:
        read()
    after = tree_fingerprint(fixture.root)

    assert after == before


def test_read_only_open_does_not_create_a_missing_database(tmp_path):
    missing = tmp_path / "does-not-exist.db"
    store = ReadOnlyHermesStore(db_path=missing)

    with pytest.raises((FileNotFoundError, sqlite3.OperationalError)):
        with store.connect():
            pass

    assert not missing.exists()


@pytest.mark.parametrize("board", ["../escape", "a/b", "", " board "])
def test_invalid_board_slugs_are_rejected(tmp_path, board):
    fixture = make_hermes_fixture(tmp_path)

    with pytest.raises(ValueError):
        ReadOnlyHermesStore.resolve_board_path(fixture.root, board)
