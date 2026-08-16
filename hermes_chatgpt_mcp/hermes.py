from __future__ import annotations

import importlib
import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Any
from urllib.parse import quote


class HermesIntegrationError(RuntimeError):
    """Raised when the canonical Hermes query boundary is unavailable."""


_BOARD_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def load_kanban_module(hermes_agent_root: Path):
    root = hermes_agent_root.expanduser().resolve()
    if not root.is_dir():
        raise HermesIntegrationError("Hermes source root does not exist")
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        return importlib.import_module("hermes_cli.kanban_db")
    except Exception as exc:  # pragma: no cover - exact import errors vary by install
        raise HermesIntegrationError("Hermes canonical Kanban module is unavailable") from exc


class ReadOnlyHermesStore:
    """Small, explicit read-only boundary around a Hermes Kanban database.

    The store deliberately does not call Hermes' normal ``connect`` or
    ``init_db`` helpers: those helpers perform migrations and other writes.
    """

    def __init__(
        self,
        *,
        db_path: Path,
        board: str | None = None,
        hermes_module: Any | None = None,
        hermes_agent_root: Path | None = None,
        log_root: Path | None = None,
    ) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.board = board or "default"
        self.hermes = hermes_module
        self.hermes_agent_root = hermes_agent_root
        self.log_root = Path(log_root).expanduser().resolve() if log_root else None

    @staticmethod
    def validate_board_slug(board: str) -> str:
        if not board or not _BOARD_SLUG.fullmatch(board):
            raise ValueError("invalid board slug")
        return board

    @classmethod
    def resolve_board_path(cls, hermes_root: Path, board: str) -> Path:
        root = Path(hermes_root).expanduser().resolve()
        slug = cls.validate_board_slug(board)
        if slug == "default":
            path = root / "kanban.db"
        else:
            path = root / "kanban" / "boards" / slug / "kanban.db"
        resolved = path.resolve()
        if root != resolved and root not in resolved.parents:
            raise ValueError("board path escapes Hermes root")
        return resolved

    @classmethod
    def from_hermes(
        cls,
        *,
        hermes_agent_root: Path,
        hermes_kanban_home: Path | None = None,
        board: str | None = None,
        log_root: Path | None = None,
    ) -> "ReadOnlyHermesStore":
        module = load_kanban_module(hermes_agent_root)
        home = (hermes_kanban_home or Path.home() / ".hermes").expanduser().resolve()
        selected = board or "default"
        db_path = cls.resolve_board_path(home, selected)
        return cls(
            db_path=db_path,
            board=selected,
            hermes_module=module,
            hermes_agent_root=Path(hermes_agent_root),
            log_root=log_root,
        )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if not self.db_path.is_file():
            raise FileNotFoundError(f"Hermes board database does not exist: {self.board}")
        uri = f"file:{quote(str(self.db_path), safe='/')}?mode=ro"
        try:
            safe_read = importlib.import_module("hermes_cli.sqlite_safe_read")
            connect_tracked = getattr(safe_read, "connect_tracked")
        except (ImportError, AttributeError):  # pragma: no cover - Hermes v0.20 provides it
            connect_tracked = None

        if connect_tracked is not None:
            conn = connect_tracked(
                uri,
                tracking_path=self.db_path,
                connect_fn=sqlite3.connect,
                uri=True,
                timeout=5.0,
                check_same_thread=False,
            )
        else:
            conn = sqlite3.connect(
                uri,
                uri=True,
                timeout=5.0,
                check_same_thread=False,
            )
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            if conn.execute("PRAGMA query_only").fetchone()[0] != 1:
                raise HermesIntegrationError("Hermes read-only connection did not enter query-only mode")
            yield conn
        finally:
            conn.close()

    def log_path(self, task_id: str) -> Path | None:
        if self.log_root is None:
            return None
        if not task_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", task_id):
            raise ValueError("invalid task id")
        path = (self.log_root / f"{task_id}.log").resolve()
        if self.log_root != path.parent:
            raise ValueError("task log path escapes Hermes board")
        return path

