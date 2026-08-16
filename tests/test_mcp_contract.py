from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx
import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app

from .fixtures import make_hermes_fixture
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


def test_health_metadata_auth_and_exact_tool_contract(tmp_path):
    asyncio.run(_test_health_metadata_auth_and_exact_tool_contract(tmp_path))


async def _test_health_metadata_auth_and_exact_tool_contract(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    auth = AuthService(settings)
    app = create_app(_adapter(fixture), settings=settings, auth_service=auth)
    token = auth.issue_access_token(client_id="test-client", subject="test-user")

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            health = await client.get("/healthz")
            assert health.status_code == 200
            assert health.json() == {"status": "ok"}

            protected = await client.get("/.well-known/oauth-protected-resource")
            assert protected.status_code == 200
            assert [value.rstrip("/") for value in protected.json()["authorization_servers"]] == [settings.public_base_url]
            assert set(protected.json()["scopes_supported"]) == {"hermes:read", "hermes:create", "offline_access"}

            metadata = await client.get("/.well-known/oauth-authorization-server")
            assert metadata.status_code == 200
            assert metadata.json()["token_endpoint_auth_methods_supported"] == ["none"]

            unauthorized = await client.post("/mcp", json={})
            assert unauthorized.status_code == 401
            assert "stack" not in unauthorized.text.lower()

            initialize = await _rpc(
                client,
                token,
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            )
            assert initialize["result"]["serverInfo"]["name"] == "hermes-chatgpt-mcp"
            listed = await _rpc(client, token, "tools/list", request_id=2)

    tools = listed["result"]["tools"]
    assert {tool["name"] for tool in tools} == {
        "get_board",
        "list_tasks",
        "get_task",
        "get_task_graph",
        "get_dispatch",
        "get_activity",
        "create_task",
    }
    readonly = [tool for tool in tools if tool["name"] != "create_task"]
    create = next(tool for tool in tools if tool["name"] == "create_task")
    assert all(tool["annotations"]["readOnlyHint"] is True for tool in readonly)
    assert all(tool["annotations"]["destructiveHint"] is False for tool in readonly)
    assert create["annotations"]["readOnlyHint"] is False
    assert create["annotations"]["destructiveHint"] is False
    assert create["annotations"]["idempotentHint"] is False
    assert all(tool["inputSchema"].get("additionalProperties", True) is False for tool in tools)
    assert set(metadata.json()["scopes_supported"]) == {"hermes:read", "hermes:create", "offline_access"}
