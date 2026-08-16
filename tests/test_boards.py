from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from hermes_chatgpt_mcp.boards import BoardResolutionError, HermesBoardResolver
from hermes_chatgpt_mcp.config import ConfigurationError, Settings

from hermes_cli import kanban_db

from .test_auth import _settings


def _write_board(root: Path, slug: str, *, name: str) -> Path:
    board_dir = root / "kanban" / "boards" / slug
    board_dir.mkdir(parents=True)
    (board_dir / "board.json").write_text(
        json.dumps({"slug": slug, "name": name, "description": f"{name} description"}) + "\n",
        encoding="utf-8",
    )
    db_path = board_dir / "kanban.db"
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(kanban_db.SCHEMA_SQL)
        connection.commit()
    finally:
        connection.close()
    return db_path


def _board_settings(root: Path, *, default: str = "board-a", read=("board-a", "board-b"), create=("board-a",)):
    return _settings().__class__(
        **{
            **_settings().__dict__,
            "hermes_kanban_home": root,
            "default_board": default,
            "kanban_read_boards": read,
            "kanban_create_boards": create,
        }
    )


def _resolver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> HermesBoardResolver:
    _write_board(tmp_path, "board-a", name="Board A")
    _write_board(tmp_path, "board-b", name="Board B")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    return HermesBoardResolver(_board_settings(tmp_path), hermes_module=kanban_db)


def test_explicit_board_resolves_exactly_without_default_fallback(tmp_path, monkeypatch):
    resolver = _resolver(tmp_path, monkeypatch)

    selected = resolver.resolve("board-b", operation="read")

    assert selected.slug == "board-b"
    assert selected.db_path == (tmp_path / "kanban" / "boards" / "board-b" / "kanban.db").resolve()

    with pytest.raises(BoardResolutionError) as error:
        resolver.resolve("unknown-board", operation="read")
    assert error.value.code == "BOARD_NOT_FOUND"


def test_default_board_uses_configured_board(tmp_path, monkeypatch):
    resolver = _resolver(tmp_path, monkeypatch)

    assert resolver.resolve(None, operation="read").slug == "board-a"


def test_create_allowlist_must_be_readable(tmp_path, monkeypatch):
    _write_board(tmp_path, "board-a", name="Board A")
    _write_board(tmp_path, "board-b", name="Board B")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    settings = _board_settings(tmp_path, read=("board-a",), create=("board-b",))

    with pytest.raises(ConfigurationError, match="CREATE"):
        HermesBoardResolver(settings, hermes_module=kanban_db)


def test_unreadable_board_is_omitted_from_discovery(tmp_path, monkeypatch):
    resolver = _resolver(tmp_path, monkeypatch)

    assert [handle.slug for handle in resolver.list_handles()] == ["board-a", "board-b"]

    restricted = HermesBoardResolver(
        _board_settings(tmp_path, read=("board-a",), create=("board-a",)),
        hermes_module=kanban_db,
    )
    assert [handle.slug for handle in restricted.list_handles()] == ["board-a"]


def test_board_path_uses_canonical_hermes_resolution(tmp_path, monkeypatch):
    resolver = _resolver(tmp_path, monkeypatch)

    selected = resolver.resolve("board-b", operation="read")

    assert selected.db_path == kanban_db.kanban_db_path(board="board-b").resolve()


def test_ambient_hermes_kanban_db_override_fails_closed(tmp_path, monkeypatch):
    _write_board(tmp_path, "board-a", name="Board A")
    _write_board(tmp_path, "board-b", name="Board B")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_KANBAN_DB", str(tmp_path / "kanban" / "boards" / "board-a" / "kanban.db"))

    with pytest.raises(ConfigurationError, match="HERMES_KANBAN_DB"):
        HermesBoardResolver(_board_settings(tmp_path), hermes_module=kanban_db)
