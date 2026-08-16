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


def _make_multi_app(tmp_path: Path, monkeypatch, *, create_boards=("board-a",)):
    _write_board(tmp_path, "board-a", name="Board A")
    _write_board(tmp_path, "board-b", name="Board B")
    _write_board(tmp_path, "board-c", name="Board C")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    task_a_id = _seed_task(tmp_path, "board-a", "seed-a", "A-only task")
    task_b_id = _seed_task(tmp_path, "board-b", "seed-b", "B-only task")
    settings = replace(_multi_settings(tmp_path), kanban_create_boards=tuple(create_boards))
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
    assert [board["is_default"] for board in boards] == [True, False]
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


def test_create_task_routes_to_a_and_b_without_cross_board_writes(tmp_path, monkeypatch):
    asyncio.run(_test_create_task_routes_to_a_and_b_without_cross_board_writes(tmp_path, monkeypatch))


async def _test_create_task_routes_to_a_and_b_without_cross_board_writes(tmp_path, monkeypatch):
    settings, auth, app, task_a_id, _ = _make_multi_app(
        tmp_path, monkeypatch, create_boards=("board-a", "board-b")
    )
    token = auth.issue_access_token(
        client_id="creator",
        subject="creator",
        scopes=["hermes:read", "hermes:create"],
    )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            before_a = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-a", "limit": 20}}}, 1,
            )
            before_b = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-b", "limit": 20}}}, 2,
            )
            created_a = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "board": "board-a", "title": "MCP multi-board A", "idempotency_key": "multi-board-a-1"
                }}}, 3,
            )
            created_b = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "board": "board-b", "title": "MCP multi-board B", "idempotency_key": "multi-board-b-1"
                }}}, 4,
            )
            duplicate_a = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "board": "board-a", "title": "retry must not duplicate", "idempotency_key": "multi-board-a-1"
                }}}, 5,
            )
            cross_board_parent = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "board": "board-b", "title": "invalid cross-board parent", "parent_ids": [task_a_id],
                    "idempotency_key": "multi-board-invalid-parent-1"
                }}}, 6,
            )
            after_a = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-a", "limit": 20}}}, 7,
            )
            after_b = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-b", "limit": 20}}}, 8,
            )
            activity_b = await _rpc(
                client, token, "tools/call",
                {"name": "get_activity", "arguments": {"request": {
                    "board": "board-b", "task_id": created_b["result"]["structuredContent"]["task_id"],
                    "max_items": 20, "log_bytes": 0
                }}}, 9,
            )

    payload_a = created_a["result"]["structuredContent"]
    payload_b = created_b["result"]["structuredContent"]
    assert payload_a["board"] == "board-a"
    assert payload_b["board"] == "board-b"
    assert duplicate_a["result"]["structuredContent"]["task_id"] == payload_a["task_id"]
    assert cross_board_parent["result"]["isError"] is True
    assert len(after_a["result"]["structuredContent"]["items"]) == len(before_a["result"]["structuredContent"]["items"]) + 1
    assert len(after_b["result"]["structuredContent"]["items"]) == len(before_b["result"]["structuredContent"]["items"]) + 1
    assert any(item["id"] == payload_a["task_id"] for item in after_a["result"]["structuredContent"]["items"])
    assert all(item["id"] != payload_a["task_id"] for item in after_b["result"]["structuredContent"]["items"])
    assert any(item["id"] == payload_b["task_id"] for item in after_b["result"]["structuredContent"]["items"])
    assert all(item["id"] != payload_b["task_id"] for item in after_a["result"]["structuredContent"]["items"])
    assert any(event["kind"] == "created" for event in activity_b["result"]["structuredContent"]["events"])


def test_create_task_rejects_readable_but_non_writable_board(tmp_path, monkeypatch):
    asyncio.run(_test_create_task_rejects_readable_but_non_writable_board(tmp_path, monkeypatch))


async def _test_create_task_rejects_readable_but_non_writable_board(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_multi_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(
        client_id="creator",
        subject="creator",
        scopes=["hermes:read", "hermes:create"],
    )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            before = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-b", "limit": 20}}}, 1,
            )
            rejected = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "board": "board-b", "title": "must be rejected", "idempotency_key": "board-b-denied-1"
                }}}, 2,
            )
            after = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-b", "limit": 20}}}, 3,
            )

    assert rejected["result"]["isError"] is True
    assert "BOARD_NOT_ALLOWED" in str(rejected)
    assert after["result"]["structuredContent"]["items"] == before["result"]["structuredContent"]["items"]


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
