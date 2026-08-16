from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import httpx

from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.server import create_app

from hermes_cli import kanban_db

from .test_auth import _settings
from .test_boards import _write_board


async def _rpc(client: httpx.AsyncClient, token: str, method: str, params=None, request_id: int = 1):
    response = await client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _multi_settings(root: Path) -> Settings:
    return replace(
        _settings(),
        hermes_kanban_home=root,
        default_board="board-a",
        kanban_read_boards=("board-a", "board-b"),
        kanban_create_boards=("board-a",),
    )


def _seed_task(root: Path, slug: str, task_id: str, title: str) -> str:
    db_path = root / "kanban" / "boards" / slug / "kanban.db"
    with kanban_db.connect_closing(db_path=db_path, board=slug) as conn:
        actual = kanban_db.create_task(
            conn,
            title=title,
            created_by="fixture",
            idempotency_key=f"seed-{task_id}",
            board=slug,
        )
        assert isinstance(actual, str) and actual
        return actual


def _make_multi_app(tmp_path: Path, monkeypatch):
    _write_board(tmp_path, "board-a", name="Board A")
    _write_board(tmp_path, "board-b", name="Board B")
    _write_board(tmp_path, "board-c", name="Board C")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    task_a_id = _seed_task(tmp_path, "board-a", "seed-a", "A-only task")
    task_b_id = _seed_task(tmp_path, "board-b", "seed-b", "B-only task")
    settings = _multi_settings(tmp_path)
    auth = AuthService(settings)
    return settings, auth, create_app(settings=settings, auth_service=auth), task_a_id, task_b_id


def test_list_boards_returns_only_authorized_canonical_boards(tmp_path, monkeypatch):
    asyncio.run(_test_list_boards_returns_only_authorized_canonical_boards(tmp_path, monkeypatch))


async def _test_list_boards_returns_only_authorized_canonical_boards(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_multi_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(
        client_id="creator",
        subject="creator",
        scopes=["hermes:read", "hermes:create"],
    )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            result = await _rpc(client, token, "tools/call", {"name": "list_boards", "arguments": {}}, 1)

    assert result["result"].get("isError") is not True
    boards = result["result"]["structuredContent"]["items"]
    assert [board["slug"] for board in boards] == ["board-a", "board-b"]
    assert boards[0]["capabilities"] == {"read": True, "create": True}
    assert boards[1]["capabilities"] == {"read": True, "create": False}
    assert all("db_path" not in board for board in boards)


def test_read_tools_route_to_explicit_board_a_and_b(tmp_path, monkeypatch):
    asyncio.run(_test_read_tools_route_to_explicit_board_a_and_b(tmp_path, monkeypatch))


async def _test_read_tools_route_to_explicit_board_a_and_b(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_multi_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(client_id="reader", subject="reader")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            board_a = await _rpc(client, token, "tools/call", {"name": "get_board", "arguments": {"request": {"board": "board-a"}}}, 1)
            board_b = await _rpc(client, token, "tools/call", {"name": "get_board", "arguments": {"request": {"board": "board-b"}}}, 2)
            tasks_a = await _rpc(client, token, "tools/call", {"name": "list_tasks", "arguments": {"request": {"board": "board-a", "limit": 20}}}, 3)
            tasks_b = await _rpc(client, token, "tools/call", {"name": "list_tasks", "arguments": {"request": {"board": "board-b", "limit": 20}}}, 4)

    assert board_a["result"]["structuredContent"]["slug"] == "board-a"
    assert board_b["result"]["structuredContent"]["slug"] == "board-b"
    assert [item["title"] for item in tasks_a["result"]["structuredContent"]["items"]] == ["A-only task"]
    assert [item["title"] for item in tasks_b["result"]["structuredContent"]["items"]] == ["B-only task"]


def test_unknown_board_does_not_fallback_to_default(tmp_path, monkeypatch):
    asyncio.run(_test_unknown_board_does_not_fallback_to_default(tmp_path, monkeypatch))


async def _test_unknown_board_does_not_fallback_to_default(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_multi_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(client_id="reader", subject="reader")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            result = await _rpc(client, token, "tools/call", {"name": "get_board", "arguments": {"request": {"board": "unknown"}}}, 1)

    assert result["result"]["isError"] is True
    assert "Board A" not in str(result)


def test_task_id_from_board_b_is_not_found_on_board_a(tmp_path, monkeypatch):
    asyncio.run(_test_task_id_from_board_b_is_not_found_on_board_a(tmp_path, monkeypatch))


async def _test_task_id_from_board_b_is_not_found_on_board_a(tmp_path, monkeypatch):
    settings, auth, app, _, task_b_id = _make_multi_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(client_id="reader", subject="reader")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            result = await _rpc(
                client,
                token,
                "tools/call",
                {"name": "get_task", "arguments": {"request": {"board": "board-a", "task_id": task_b_id}}},
                1,
            )

    assert result["result"]["isError"] is True
