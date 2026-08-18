from __future__ import annotations

import asyncio

import httpx

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app

from .fixtures import make_hermes_fixture, tree_fingerprint
from .test_auth import _settings


def test_create_task_scope_isolation_and_real_command_path(tmp_path):
    asyncio.run(_test_create_task_scope_isolation_and_real_command_path(tmp_path))


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


async def _test_create_task_scope_isolation_and_real_command_path(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    from hermes_cli import kanban_db

    store = ReadOnlyHermesStore(
        db_path=fixture.db_path,
        board=fixture.board,
        hermes_module=kanban_db,
        log_root=fixture.log_path.parent,
    )
    settings = _settings()
    auth = AuthService(settings)
    app = create_app(HermesReadOnlyAdapter(store), settings=settings, auth_service=auth)
    read_token = auth.issue_access_token(client_id="read", subject="reader")
    create_token = auth.issue_access_token(
        client_id="creator",
        subject="creator",
        scopes=["hermes:read", "hermes:create"],
        board=fixture.board,
        board_access="write",
    )
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _rpc(
                client,
                read_token,
                "initialize",
                {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "read", "version": "0"}},
                1,
            )
            denied_before = tree_fingerprint(fixture.root)
            denied = await _rpc(
                client,
                read_token,
                "tools/call",
                {"name": "create_task", "arguments": {"request": {"title": "must be denied", "idempotency_key": "denied-1"}}},
                2,
            )
            assert denied["result"]["isError"] is True
            assert "hermes:create" in str(denied)
            assert tree_fingerprint(fixture.root) == denied_before

            missing_key_before = tree_fingerprint(fixture.root)
            missing_key = await _rpc(
                client,
                create_token,
                "tools/call",
                {"name": "create_task", "arguments": {"request": {"title": "must be idempotent"}}},
                21,
            )
            assert missing_key["result"]["isError"] is True
            assert "idempotency_key" in str(missing_key)
            assert tree_fingerprint(fixture.root) == missing_key_before

            await _rpc(
                client,
                create_token,
                "initialize",
                {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "creator", "version": "0"}},
                3,
            )
            created = await _rpc(
                client,
                create_token,
                "tools/call",
                {
                    "name": "create_task",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "title": "Created through MCP",
                            "body": "Acceptance criteria belong in Hermes body in v0.2.",
                            "assignee": "worker",
                            "priority": 9,
                            "tenant": "tenant-a",
                            "session_id": "mcp-test-session",
                            "idempotency_key": "mcp-integration-1",
                        }
                    },
                },
                4,
            )
            assert created["result"].get("isError") is not True, created
            payload = created["result"]["structuredContent"]
            assert payload["created"] is True
            task_id = payload["task_id"]
            assert payload["status"] == "ready"
            assert payload["board"] == fixture.board

            duplicate = await _rpc(
                client,
                create_token,
                "tools/call",
                {"name": "create_task", "arguments": {"request": {"title": "different title", "idempotency_key": "mcp-integration-1"}}},
                5,
            )
            assert duplicate["result"].get("isError") is not True, duplicate
            dup_payload = duplicate["result"]["structuredContent"]
            assert dup_payload["task_id"] == task_id
            assert dup_payload["created"] is False
            assert dup_payload["idempotent_replay"] is True

            read_back = await _rpc(
                client,
                read_token,
                "tools/call",
                {"name": "get_task", "arguments": {"request": {"task_id": task_id}}},
                6,
            )
            assert read_back["result"]["structuredContent"]["id"] == task_id
            assert read_back["result"]["structuredContent"]["created_by"] == "chatgpt_mcp"

            activity = await _rpc(
                client,
                read_token,
                "tools/call",
                {"name": "get_activity", "arguments": {"request": {"task_id": task_id, "max_items": 20, "log_bytes": 0}}},
                7,
            )
            assert any(event["kind"] == "created" for event in activity["result"]["structuredContent"]["events"])
            dispatch = await _rpc(
                client,
                read_token,
                "tools/call",
                {"name": "get_dispatch", "arguments": {"request": {"task_id": task_id}}},
                8,
            )
            assert dispatch["result"]["structuredContent"]["state"] == "READY"

            invalid_before = {row["id"] for row in (await _rpc(
                client,
                read_token,
                "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"limit": 100, "include_archived": True}}},
                9,
            ))["result"]["structuredContent"]["items"]}
            invalid = await _rpc(
                client,
                create_token,
                "tools/call",
                {"name": "create_task", "arguments": {"request": {"title": "invalid", "parent_ids": ["missing-parent"], "idempotency_key": "invalid-parent-1"}}},
                10,
            )
            assert invalid["result"]["isError"] is True
            invalid_after = {row["id"] for row in (await _rpc(
                client,
                read_token,
                "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"limit": 100, "include_archived": True}}},
                11,
            ))["result"]["structuredContent"]["items"]}
            assert invalid_after == invalid_before
