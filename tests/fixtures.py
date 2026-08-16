from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from hermes_cli import kanban_db


@dataclass(frozen=True)
class HermesFixture:
    root: Path
    board: str
    db_path: Path
    log_path: Path


def _insert_fixture_rows(conn: sqlite3.Connection) -> None:
    task_columns = (
        "id, title, body, assignee, status, priority, created_by, created_at, "
        "started_at, completed_at, tenant, result, consecutive_failures, "
        "last_failure_error, current_run_id, session_id, block_kind, block_recurrences"
    )
    rows = [
        (
            "root",
            "Root task",
            "Canonical root body",
            "planner",
            "done",
            1,
            "fixture",
            1_700_000_000,
            1_700_000_010,
            1_700_000_020,
            "tenant-a",
            "root result",
            0,
            None,
            None,
            "session-a",
            None,
            0,
        ),
        (
            "child-ready",
            "Ready child",
            "Ready body",
            "worker",
            "ready",
            2,
            "fixture",
            1_700_000_001,
            None,
            None,
            "tenant-a",
            None,
            0,
            None,
            None,
            "session-a",
            None,
            0,
        ),
        (
            "child-blocked",
            "Blocked child",
            "Blocked body",
            None,
            "blocked",
            3,
            "fixture",
            1_700_000_002,
            None,
            None,
            "tenant-a",
            None,
            2,
            "provider unavailable",
            None,
            "session-b",
            "provider",
            1,
        ),
        (
            "review-task",
            "Review task",
            "Review body",
            "reviewer",
            "review",
            4,
            "fixture",
            1_700_000_003,
            1_700_000_004,
            None,
            "tenant-b",
            None,
            0,
            None,
            7,
            None,
            None,
            0,
        ),
        (
            "archived-task",
            "Archived task",
            "Archived body",
            None,
            "archived",
            5,
            "fixture",
            1_700_000_005,
            None,
            1_700_000_006,
            "tenant-b",
            "archived result",
            0,
            None,
            None,
            None,
            None,
            0,
        ),
    ]
    conn.executemany(
        f"INSERT INTO tasks ({task_columns}) VALUES ({','.join('?' for _ in task_columns.split(', '))})",
        rows,
    )
    conn.executemany(
        "INSERT INTO task_links (parent_id, child_id) VALUES (?, ?)",
        [("root", "child-ready"), ("root", "child-blocked")],
    )
    conn.execute(
        "INSERT INTO task_comments (task_id, author, body, created_at) VALUES (?, ?, ?, ?)",
        ("review-task", "reviewer", "Please inspect evidence", 1_700_000_100),
    )
    conn.execute(
        "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        ("review-task", 7, "review_requested", json.dumps({"source": "fixture"}), 1_700_000_101),
    )
    conn.execute(
        """INSERT INTO task_runs
           (id, task_id, profile, status, started_at, ended_at, outcome, summary,
            metadata, error)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (7, "review-task", "worker", "done", 1_700_000_040, 1_700_000_050,
         "completed", "Review handoff", json.dumps({"safe": True}), None),
    )
    conn.execute(
        """INSERT INTO task_attachments
           (task_id, filename, stored_path, content_type, size, uploaded_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("review-task", "evidence.txt", "/secret/should-not-leak.txt", "text/plain", 12, "reviewer", 1_700_000_102),
    )


def make_hermes_fixture(tmp_path: Path) -> HermesFixture:
    root = tmp_path / "hermes-root"
    board = "fixture-board"
    board_dir = root / "kanban" / "boards" / board
    board_dir.mkdir(parents=True)
    (board_dir / "board.json").write_text(
        json.dumps({"name": "Fixture Board", "description": "Representative board"}) + "\n",
        encoding="utf-8",
    )
    db_path = board_dir / "kanban.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(kanban_db.SCHEMA_SQL)
        _insert_fixture_rows(conn)
        conn.commit()
    finally:
        conn.close()
    log_path = board_dir / "logs" / "review-task.log"
    log_path.parent.mkdir()
    log_path.write_text("worker started\nreview evidence\n", encoding="utf-8")
    return HermesFixture(root=root, board=board, db_path=db_path, log_path=log_path)


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return "missing"
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()
