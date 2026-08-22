from __future__ import annotations

import asyncio
import re

import httpx

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app
from hermes_chatgpt_mcp.ui import KANBAN_UI_MAX_BYTES, KANBAN_UI_RESOURCE_URI, build_kanban_ui_html

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


def test_kanban_ui_html_is_static_safe_and_versioned():
    html = build_kanban_ui_html()
    assert html.startswith("<!DOCTYPE html>")
    assert 'data-ui-version="v1"' in html
    assert len(html.encode()) <= KANBAN_UI_MAX_BYTES
    assert re.match(r"^ui://hermes/kanban/v\d+$", KANBAN_UI_RESOURCE_URI)
    for token in (
        "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
        "new Function", "srcdoc", "javascript:", "fetch(", "XMLHttpRequest",
        "WebSocket", "EventSource", "localStorage", "sessionStorage", "indexedDB",
        "http://", "https://",
    ):
        assert token not in html


def test_mcp_ui_resource_registration_and_fallback(tmp_path):
    asyncio.run(_test_mcp_ui_resource_registration_and_fallback(tmp_path))


async def _test_mcp_ui_resource_registration_and_fallback(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    auth = AuthService(settings)
    app = create_app(_adapter(fixture), settings=settings, auth_service=auth)
    token = auth.issue_access_token(client_id="ui-test", subject="test")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _rpc(client, token, "initialize", {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "ui-test", "version": "0"},
            }, 1)
            tools = (await _rpc(client, token, "tools/list", {}, 2))["result"]["tools"]
            linked = [tool for tool in tools if tool.get("_meta", {}).get("ui")]
            assert [tool["name"] for tool in linked] == ["get_board"]
            assert linked[0]["_meta"]["ui"]["resourceUri"] == KANBAN_UI_RESOURCE_URI
            resources = (await _rpc(client, token, "resources/list", {}, 3))["result"]["resources"]
            resource = next(item for item in resources if item["uri"] == KANBAN_UI_RESOURCE_URI)
            assert resource["mimeType"] == "text/html;profile=mcp-app"
            read = await _rpc(client, token, "resources/read", {"uri": KANBAN_UI_RESOURCE_URI}, 4)
            content = read["result"]["contents"][0]
            assert content["text"].startswith("<!DOCTYPE html>")
            assert content["mimeType"] == "text/html;profile=mcp-app"
            result = await _rpc(client, token, "tools/call", {"name": "get_board", "arguments": {"request": {}}}, 5)
            assert result["result"]["structuredContent"]
            assert any(item.get("type") == "text" and item.get("text") for item in result["result"]["content"])
