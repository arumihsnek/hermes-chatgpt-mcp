#!/usr/bin/env python3
"""Read-only smoke test against the actual Hermes installation and board."""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore


def _fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _settled_fingerprint(paths: list[Path], expected: str, *, timeout: float = 3.0) -> str:
    """Allow SQLite to remove transient WAL/SHM coordination sidecars."""
    current = _fingerprint(paths)
    deadline = time.monotonic() + timeout
    while current != expected and time.monotonic() < deadline:
        time.sleep(0.1)
        current = _fingerprint(paths)
    return current


def main() -> int:
    if os.environ.get("HERMES_LIVE_TEST") != "1":
        raise SystemExit("refusing live smoke without HERMES_LIVE_TEST=1")
    agent_root = Path(os.environ.get("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")).expanduser().resolve()
    kanban_home = Path(os.environ.get("HERMES_KANBAN_HOME", "/home/ubuntu/.hermes")).expanduser().resolve()
    board = os.environ.get("HERMES_KANBAN_BOARD", "").strip()
    if not board:
        raise SystemExit("set HERMES_KANBAN_BOARD explicitly; live smoke refuses an ambiguous board")

    store = ReadOnlyHermesStore.from_hermes(
        hermes_agent_root=agent_root,
        hermes_kanban_home=kanban_home,
        board=board,
    )
    adapter = HermesReadOnlyAdapter(store)
    tracked_paths = [store.db_path, Path(f"{store.db_path}-wal"), Path(f"{store.db_path}-shm"), store.db_path.parent / "board.json"]
    before = _fingerprint(tracked_paths)
    board_view = adapter.get_board()
    task_list = adapter.list_tasks(limit=10, include_archived=True)
    if not task_list.items:
        raise SystemExit("live board has no task to exercise task-scoped tools")
    task_id = task_list.items[0].id
    task = adapter.get_task(task_id)
    graph = adapter.get_task_graph(task_id, depth=1, max_nodes=25)
    dispatch = adapter.get_dispatch(task_id)
    activity = adapter.get_activity(task_id, max_items=25, log_bytes=4_000)
    after = _settled_fingerprint(tracked_paths, before)
    if after != before:
        raise SystemExit("FAIL: live read-only fingerprint changed")

    print(f"PASS board={board_view.slug} statuses={len(board_view.task_counts)} tasks={len(task_list.items)}")
    print(f"PASS task={task.id} graph_nodes={len(graph.nodes)} dispatch={dispatch.state} events={len(activity.events)} runs={len(activity.runs)}")
    print("PASS six canonical read operations completed; tracked Hermes state unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
