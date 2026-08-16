from __future__ import annotations

import asyncio

import httpx

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app

from .fixtures import make_hermes_fixture, tree_fingerprint
from .test_auth import _settings


def _adapter(fixture):
    from hermes_cli import kanban_db

    return HermesReadOnlyAdapter(
        ReadOnlyHermesStore(
            db_path=fixture.db_path,
            board=fixture.board,
            hermes_module=kanban_db,
            log_root=fixture.log_path.parent,
        )
    )


async def _rpc(client, token, method, params, request_id):
    response = await client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_every_mcp_tool_preserves_fixture_state(tmp_path):
    asyncio.run(_test_every_mcp_tool_preserves_fixture_state(tmp_path))


async def _test_every_mcp_tool_preserves_fixture_state(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    auth = AuthService(settings)
    app = create_app(_adapter(fixture), settings=settings, auth_service=auth)
    token = auth.issue_access_token(client_id="readonly-test", subject="test")
    calls = [
        ("get_board", {"request": {}}),
        ("list_tasks", {"request": {"limit": 10, "include_archived": True}}),
        ("get_task", {"request": {"task_id": "review-task"}}),
        ("get_task_graph", {"request": {"task_id": "child-ready", "depth": 1, "max_nodes": 10}}),
        ("get_dispatch", {"request": {"task_id": "child-blocked"}}),
        ("get_activity", {"request": {"task_id": "review-task", "max_items": 10, "log_bytes": 1000}}),
    ]
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _rpc(client, token, "initialize", {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "readonly-test", "version": "0"},
            }, 1)
            for index, (name, arguments) in enumerate(calls, start=2):
                before = tree_fingerprint(fixture.root)
                result = await _rpc(client, token, "tools/call", {"name": name, "arguments": arguments}, index)
                after = tree_fingerprint(fixture.root)
                assert result["result"].get("isError") is not True, (name, result)
                assert after == before, name


def test_unknown_task_and_unknown_tool_are_sanitized(tmp_path):
    asyncio.run(_test_unknown_task_and_unknown_tool_are_sanitized(tmp_path))


async def _test_unknown_task_and_unknown_tool_are_sanitized(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    auth = AuthService(settings)
    app = create_app(_adapter(fixture), settings=settings, auth_service=auth)
    token = auth.issue_access_token(client_id="readonly-test", subject="test")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _rpc(client, token, "initialize", {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "readonly-test", "version": "0"},
            }, 1)
            missing = await _rpc(client, token, "tools/call", {"name": "get_task", "arguments": {"request": {"task_id": "missing"}}}, 2)
            assert missing["result"]["isError"] is True
            assert "traceback" not in str(missing).lower()
            unknown = await _rpc(client, token, "tools/call", {"name": "create_task", "arguments": {}}, 3)
            assert unknown["result"]["isError"] is True
            assert "create" not in str(unknown).lower() or "unknown" in str(unknown).lower()

