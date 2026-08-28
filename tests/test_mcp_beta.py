from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.boards import HermesBoardResolver
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app

from hermes_cli import kanban_db

from .fixtures import make_hermes_fixture, tree_fingerprint
from .test_auth import _settings
from .test_boards import _write_board


async def _rpc(
    client: httpx.AsyncClient,
    token: str,
    method: str,
    params: dict | None = None,
    request_id: int = 1,
) -> dict:
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


def _stable_adapter(fixture) -> HermesReadOnlyAdapter:
    return HermesReadOnlyAdapter(
        ReadOnlyHermesStore(
            db_path=fixture.db_path,
            board=fixture.board,
            hermes_module=kanban_db,
            log_root=fixture.log_path.parent,
        )
    )


def _beta_app(tmp_path: Path, monkeypatch, *, board_create_enabled: bool = True):
    fixture = make_hermes_fixture(tmp_path)
    _write_board(fixture.root, "other-board", name="Other Board")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    kanban_db.set_current_board(fixture.board)
    settings = replace(
        _settings(),
        hermes_kanban_home=fixture.root,
        default_board=fixture.board,
        kanban_read_boards=None,
        kanban_create_boards=None,
        surface="beta",
        board_create_enabled=board_create_enabled,
    )
    auth = AuthService(settings)
    resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    app = create_app(
        board_resolver=resolver,
        settings=settings,
        auth_service=auth,
        surface="beta",
    )
    return fixture, settings, auth, resolver, app


def _token(
    auth: AuthService,
    client_id: str,
    scopes: list[str],
    *,
    board: str | None = None,
) -> str:
    return auth.issue_access_token(
        client_id=client_id,
        subject=client_id,
        scopes=scopes,
        board=board,
        board_access="write" if board else None,
    )


def _assert_tool_error(result: dict, code: str, *, forbidden_path: Path | None = None) -> None:
    assert result["result"]["isError"] is True
    rendered = str(result)
    assert f'"code":"{code}"' in rendered
    assert "Traceback" not in rendered
    assert "stack" not in rendered.lower()
    if forbidden_path is not None:
        assert str(forbidden_path) not in rendered


def test_settings_beta_derives_beta_mcp_surface_without_explicit_override(tmp_path, monkeypatch):
    asyncio.run(_test_settings_beta_derives_beta_mcp_surface_without_explicit_override(tmp_path, monkeypatch))


def test_chatgpt_compat_mode_freezes_exact_v41_tool_contract(tmp_path, monkeypatch):
    asyncio.run(_test_chatgpt_compat_mode_freezes_exact_v41_tool_contract(tmp_path, monkeypatch))


async def _test_chatgpt_compat_mode_freezes_exact_v41_tool_contract(tmp_path, monkeypatch):
    fixture, settings, auth, resolver, _ = _beta_app(tmp_path, monkeypatch)
    settings = replace(settings, chatgpt_compat_mode=True)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")
    token = _token(auth, "compat", ["hermes:read", "hermes:manage", "hermes:board:create"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            response = await client.post(
                "/mcp",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-06-18",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
    assert response.status_code == 200
    assert {tool["name"] for tool in response.json()["result"]["tools"]} == {
        "list_boards", "get_board", "list_tasks", "get_task", "get_task_graph",
        "get_dispatch", "get_activity", "create_task", "create_board",
        "add_comment", "assign_task", "get_run", "list_runs", "active_workers",
        "bounded_log", "runtime_status", "attachments", "control-status", "canary",
        "diagnostics", "update_task",
    }


def test_stateless_chatgpt_matrix_does_not_require_session_replay(tmp_path, monkeypatch):
    asyncio.run(_test_stateless_chatgpt_matrix_does_not_require_session_replay(tmp_path, monkeypatch))


async def _test_stateless_chatgpt_matrix_does_not_require_session_replay(tmp_path, monkeypatch):
    fixture, settings, auth, resolver, _ = _beta_app(tmp_path, monkeypatch)
    settings = replace(settings, chatgpt_compat_mode=True)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")
    token = _token(auth, "matrix", ["hermes:read", "hermes:manage", "hermes:board:create"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)
    base_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
    }
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "matrix", "version": "1"}}}
    listed = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            first = await client.post("/mcp", headers=base_headers, json=initialize)
            assert first.status_code == 200
            assert "mcp-session-id" not in first.headers
            for session_id in (None, "stale-session", "wrong-session"):
                headers = dict(base_headers)
                if session_id:
                    headers["MCP-Session-Id"] = session_id
                repeated = await client.post("/mcp", headers=headers, json=listed)
                assert repeated.status_code == 200, repeated.text
                assert "mcp-session-id" not in repeated.headers


async def _test_settings_beta_derives_beta_mcp_surface_without_explicit_override(tmp_path, monkeypatch):
    _, settings, auth, resolver, _ = _beta_app(tmp_path, monkeypatch)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth)
    token = _token(auth, "manager", ["hermes:read", "hermes:manage"], board="fixture-board")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            tools = (await _rpc(client, token, "tools/list"))["result"]["tools"]

    assert {tool["name"] for tool in tools} >= {
        "list_boards",
        "get_board",
        "list_tasks",
        "get_task",
        "get_task_graph",
        "get_dispatch",
        "get_activity",
        "create_task",
        "create_board",
        "add_comment",
        "assign_task",
    }


@pytest.mark.parametrize(
    ("settings_surface", "explicit_surface"),
    [("beta", "stable"), ("stable", "beta")],
)
def test_create_app_rejects_surface_selector_mismatch(settings_surface, explicit_surface):
    settings = replace(_settings(), surface=settings_surface)

    with pytest.raises(ValueError, match="surface"):
        create_app(settings=settings, surface=explicit_surface, board_resolver=object())


@pytest.mark.parametrize(
    ("settings_surface", "auth_surface"),
    [("beta", "stable"), ("stable", "beta")],
)
def test_create_app_rejects_injected_auth_policy_mismatch(settings_surface, auth_surface):
    settings = replace(_settings(), surface=settings_surface)
    auth = AuthService(replace(settings, surface=auth_surface))

    with pytest.raises(ValueError, match="policy"):
        create_app(settings=settings, auth_service=auth, board_resolver=object())


def test_beta_manage_scope_is_offered_one_board_oauth_authorization():
    settings = replace(_settings(), surface="beta")
    form = AuthService(settings).authorization_form(
        query={"scope": "hermes:read hermes:manage"},
        board_options=[{"slug": "board-a", "name": "Board A"}],
        default_board="board-a",
    )

    assert "value='write'" in form
    assert "name='board'" in form
    assert "value=\"board-a\"" in form


def test_stable_default_and_beta_tool_discovery_are_exact(tmp_path, monkeypatch):
    asyncio.run(_test_stable_default_and_beta_tool_discovery_are_exact(tmp_path, monkeypatch))


async def _test_beta_protocol_dispatches_every_discovered_name_without_writes(tmp_path, monkeypatch):
    """Separate MCP dispatch from the external ChatGPT connector resolver.

    ChatGPT's ``api_tool.list_resources`` layer is outside this repository.
    This test proves the narrower server-side boundary: every name returned by
    the same HTTP ``tools/list`` surface is known to the subsequent HTTP
    ``tools/call`` dispatcher. Empty arguments deliberately stop at schema or
    scope validation for request-bearing tools, so this is a no-mutation probe.
    """
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    token = _token(auth, "protocol-boundary-reader", ["hermes:read"])
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            first = await _rpc(client, token, "tools/list", request_id=1)
            second = await _rpc(client, token, "tools/list", request_id=2)
            first_tools = first["result"]["tools"]
            second_tools = second["result"]["tools"]
            first_names = [tool["name"] for tool in first_tools]
            second_names = [tool["name"] for tool in second_tools]

            assert first_names == second_names
            assert len(first_names) == len(set(first_names))
            assert first["result"].get("nextCursor") in (None, "")
            assert second["result"].get("nextCursor") in (None, "")

            for request_id, name, arguments in (
                (3, "list_boards", {}),
                (4, "get_board", {"request": {"board": fixture.board}}),
                (5, "tail", {"request": {"board": fixture.board, "task_id": "review-task", "limit": 1}}),
                (6, "watch", {"request": {"board": fixture.board, "task_id": "review-task", "limit": 1}}),
            ):
                stable_call = await _rpc(
                    client,
                    token,
                    "tools/call",
                    {"name": name, "arguments": arguments},
                    request_id=request_id,
                )
                assert "error" not in stable_call, (name, stable_call)
                assert isinstance(stable_call.get("result"), dict), (name, stable_call)

            third = await _rpc(client, token, "tools/list", request_id=7)
            assert [tool["name"] for tool in third["result"]["tools"]] == first_names

            for request_id, name in enumerate(first_names, start=10):
                dispatched = await _rpc(
                    client,
                    token,
                    "tools/call",
                    {"name": name, "arguments": {}},
                    request_id=request_id,
                )
                assert "error" not in dispatched, (name, dispatched)
                assert isinstance(dispatched.get("result"), dict), (name, dispatched)


def test_beta_protocol_dispatches_every_discovered_name_without_writes(tmp_path, monkeypatch):
    asyncio.run(_test_beta_protocol_dispatches_every_discovered_name_without_writes(tmp_path, monkeypatch))


async def _test_stable_default_and_beta_tool_discovery_are_exact(tmp_path, monkeypatch):
    stable_fixture = make_hermes_fixture(tmp_path / "stable")
    stable_settings = _settings()
    stable_auth = AuthService(stable_settings)
    stable_app = create_app(
        _stable_adapter(stable_fixture),
        settings=stable_settings,
        auth_service=stable_auth,
    )
    stable_token = stable_auth.issue_access_token(client_id="stable", subject="stable")
    stable_transport = httpx.ASGITransport(app=stable_app)
    async with stable_app.router.lifespan_context(stable_app):
        async with httpx.AsyncClient(
            transport=stable_transport,
            base_url=stable_settings.public_base_url,
        ) as client:
            stable_tools = (await _rpc(client, stable_token, "tools/list"))["result"]["tools"]
            stable_metadata = await client.get("/.well-known/oauth-authorization-server")

    assert {tool["name"] for tool in stable_tools} == {
        "list_boards",
        "get_board",
        "list_tasks",
        "get_task",
        "get_task_graph",
        "get_dispatch",
        "get_activity",
        "create_task",
        "get_human_gate_readback",
    }
    assert set(stable_metadata.json()["scopes_supported"]) == {
        "hermes:read",
        "hermes:create",
        "offline_access",
    }

    _, settings, auth, _, app = _beta_app(tmp_path / "beta", monkeypatch)
    token = _token(auth, "manager", ["hermes:read", "hermes:manage"], board="fixture-board")
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            tools = (await _rpc(client, token, "tools/list"))["result"]["tools"]
            metadata = await client.get("/.well-known/oauth-authorization-server")

    assert {tool["name"] for tool in tools} >= {
        "list_boards",
        "get_board",
        "list_tasks",
        "get_task",
        "get_task_graph",
        "get_dispatch",
        "get_activity",
        "create_task",
        "create_board",
        "add_comment",
        "assign_task",
    }
    assert set(metadata.json()["scopes_supported"]) == {
        "hermes:read",
        "hermes:create",
        "hermes:manage",
        "hermes:board:create",
        "hermes:admin",
        "offline_access",
    }
    beta_create_description = next(
        tool["description"] for tool in tools if tool["name"] == "create_task"
    )
    assert "only mutating tool" not in beta_create_description.lower()
    stable_create_description = next(
        tool["description"] for tool in stable_tools if tool["name"] == "create_task"
    )
    assert "only mutating tool on the stable surface" in stable_create_description.lower()
    mutation_tools = {
        tool["name"]: tool
        for tool in tools
        if tool["name"] in {"create_task", "create_board", "add_comment", "assign_task"}
    }
    assert {name: tool["annotations"] for name, tool in mutation_tools.items()} == {
        "create_task": {
            "title": "Create Hermes task",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "create_board": {
            "title": "Create Hermes board",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "add_comment": {
            "title": "Manage Hermes card",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
        "assign_task": {
            "title": "Manage Hermes card",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    }
    assert "board" not in mutation_tools["create_board"]["inputSchema"]["$defs"]["CreateBoardInput"]["properties"]
    assert all(tool["inputSchema"].get("additionalProperties", True) is False for tool in tools)


def test_beta_root_post_serves_the_mcp_transport_like_mcp(tmp_path, monkeypatch):
    asyncio.run(_test_beta_root_post_serves_the_mcp_transport_like_mcp(tmp_path, monkeypatch))


async def _test_beta_root_post_serves_the_mcp_transport_like_mcp(tmp_path, monkeypatch):
    _, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    token = _token(auth, "manager", ["hermes:read", "hermes:manage"], board="fixture-board")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
    }
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            denied = await client.post(
                "/",
                headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
            assert denied.status_code == 401, denied.text

            init = await client.post(
                "/",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "root-alias-test", "version": "0.0.1"},
                    },
                },
            )
            assert init.status_code == 200, init.text

            listed = await client.post(
                "/",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            )
            assert listed.status_code == 200, listed.text
            tools = listed.json()["result"]["tools"]

    assert {tool["name"] for tool in tools} >= {
        "list_boards",
        "get_board",
        "list_tasks",
        "get_task",
        "get_task_graph",
        "get_dispatch",
        "get_activity",
        "create_task",
        "create_board",
        "add_comment",
        "assign_task",
    }


def test_beta_capability_projection_is_scope_and_board_bound(tmp_path, monkeypatch):
    asyncio.run(_test_beta_capability_projection_is_scope_and_board_bound(tmp_path, monkeypatch))


async def _test_beta_capability_projection_is_scope_and_board_bound(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    manager = _token(auth, "manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    administrator = _token(auth, "administrator", ["hermes:read", "hermes:board:create"])
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            managed = await _rpc(client, manager, "tools/call", {"name": "list_boards", "arguments": {}}, 1)
            administrative = await _rpc(
                client,
                administrator,
                "tools/call",
                {"name": "list_boards", "arguments": {}},
                2,
            )

    managed_payload = managed["result"]["structuredContent"]
    managed_boards = {item["slug"]: item for item in managed_payload["items"]}
    assert managed_boards[fixture.board]["capabilities"] == {
        "read": True,
        "create": False,
        "manage": True,
    }
    assert managed_boards["other-board"]["capabilities"] == {
        "read": True,
        "create": False,
        "manage": False,
    }
    assert managed_payload["global_capabilities"] == {"create_board": False}
    administrative_payload = administrative["result"]["structuredContent"]
    assert administrative_payload["global_capabilities"] == {"create_board": True}
    assert all(not item["capabilities"]["manage"] for item in administrative_payload["items"])


def test_scope_failures_happen_before_command_adapter_construction(tmp_path, monkeypatch):
    asyncio.run(_test_scope_failures_happen_before_command_adapter_construction(tmp_path, monkeypatch))


async def _test_scope_failures_happen_before_command_adapter_construction(tmp_path, monkeypatch):
    fixture, settings, auth, resolver, app = _beta_app(tmp_path, monkeypatch)

    def forbidden_factory(*_args, **_kwargs):
        raise AssertionError("command adapter must not be constructed")

    monkeypatch.setattr(resolver, "board_admin_adapter", forbidden_factory)
    monkeypatch.setattr(resolver, "command_adapter", forbidden_factory)
    monkeypatch.setattr(resolver, "management_adapter", forbidden_factory)
    read = _token(auth, "reader", ["hermes:read"])
    creator = _token(auth, "creator", ["hermes:read", "hermes:create"], board=fixture.board)
    administrator = _token(auth, "administrator", ["hermes:read", "hermes:board:create"])
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            denied = [
                await _rpc(
                    client,
                    read,
                    "tools/call",
                    {"name": "create_board", "arguments": {"request": {"slug": "denied-read"}}},
                    1,
                ),
                await _rpc(
                    client,
                    creator,
                    "tools/call",
                    {"name": "create_board", "arguments": {"request": {"slug": "denied-create"}}},
                    2,
                ),
                await _rpc(
                    client,
                    read,
                    "tools/call",
                    {
                        "name": "add_comment",
                        "arguments": {"request": {"board": fixture.board, "task_id": "review-task", "body": "denied"}},
                    },
                    3,
                ),
                await _rpc(
                    client,
                    administrator,
                    "tools/call",
                    {
                        "name": "assign_task",
                        "arguments": {"request": {"board": fixture.board, "task_id": "review-task", "assignee": "planner"}},
                    },
                    4,
                ),
                await _rpc(
                    client,
                    read,
                    "tools/call",
                    {
                        "name": "create_task",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "title": "must not construct",
                                "idempotency_key": "ordering-read-create-1",
                            }
                        },
                    },
                    5,
                ),
            ]

    for result in denied:
        _assert_tool_error(result, "SCOPE_REQUIRED", forbidden_path=fixture.root)


def test_board_creation_requires_admin_scope_and_feature_gate(tmp_path, monkeypatch):
    asyncio.run(_test_board_creation_requires_admin_scope_and_feature_gate(tmp_path, monkeypatch))


async def _test_board_creation_requires_admin_scope_and_feature_gate(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path / "enabled", monkeypatch)
    administrator = _token(auth, "administrator", ["hermes:read", "hermes:board:create"])
    current_before = kanban_db.get_current_board()
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            created = await _rpc(
                client,
                administrator,
                "tools/call",
                {
                    "name": "create_board",
                    "arguments": {
                        "request": {
                            "slug": "created-via-mcp",
                            "name": "Created via MCP",
                            "description": "Canonical beta board",
                        }
                    },
                },
                1,
            )

    assert created["result"].get("isError") is not True, created
    assert created["result"]["structuredContent"]["slug"] == "created-via-mcp"
    assert (fixture.root / "kanban" / "boards" / "created-via-mcp" / "kanban.db").is_file()
    assert kanban_db.get_current_board() == current_before

    disabled_fixture, disabled_settings, disabled_auth, _, disabled_app = _beta_app(
        tmp_path / "disabled",
        monkeypatch,
        board_create_enabled=False,
    )
    disabled_token = _token(
        disabled_auth,
        "disabled-administrator",
        ["hermes:read", "hermes:board:create"],
    )
    disabled_transport = httpx.ASGITransport(app=disabled_app)
    before = tree_fingerprint(disabled_fixture.root)
    async with disabled_app.router.lifespan_context(disabled_app):
        async with httpx.AsyncClient(
            transport=disabled_transport,
            base_url=disabled_settings.public_base_url,
        ) as client:
            denied = await _rpc(
                client,
                disabled_token,
                "tools/call",
                {"name": "create_board", "arguments": {"request": {"slug": "feature-disabled"}}},
                2,
            )
    _assert_tool_error(denied, "BOARD_CREATE_DISABLED", forbidden_path=disabled_fixture.root)
    assert tree_fingerprint(disabled_fixture.root) == before


def test_create_board_normalizes_slug_before_acquiring_route_lock(tmp_path, monkeypatch):
    asyncio.run(_test_create_board_normalizes_slug_before_acquiring_route_lock(tmp_path, monkeypatch))


async def _test_create_board_normalizes_slug_before_acquiring_route_lock(tmp_path, monkeypatch):
    fixture, settings, auth, resolver, app = _beta_app(tmp_path, monkeypatch)
    administrator = _token(auth, "administrator", ["hermes:read", "hermes:board:create"])
    observed: list[str] = []
    original_creation_lock = resolver.creation_lock

    def recording_creation_lock(slug):
        observed.append(slug)
        return original_creation_lock(slug)

    monkeypatch.setattr(resolver, "creation_lock", recording_creation_lock)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            result = await _rpc(
                client,
                administrator,
                "tools/call",
                {"name": "create_board", "arguments": {"request": {"slug": "Case-Locked-Board"}}},
                1,
            )

    assert result["result"].get("isError") is not True, result
    assert observed == ["case-locked-board"]


def test_public_board_creation_returns_safe_conflicts_for_reserved_and_archived_slugs(tmp_path, monkeypatch):
    asyncio.run(_test_public_board_creation_returns_safe_conflicts_for_reserved_and_archived_slugs(tmp_path, monkeypatch))


async def _test_public_board_creation_returns_safe_conflicts_for_reserved_and_archived_slugs(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    kanban_db.create_board("archived-public-board", name="Archived Public Board")
    kanban_db.remove_board("archived-public-board", archive=True)
    administrator = _token(auth, "administrator", ["hermes:read", "hermes:board:create"])
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            reserved = await _rpc(
                client,
                administrator,
                "tools/call",
                {"name": "create_board", "arguments": {"request": {"slug": "default"}}},
                1,
            )
            archived = await _rpc(
                client,
                administrator,
                "tools/call",
                {"name": "create_board", "arguments": {"request": {"slug": "ARCHIVED-PUBLIC-BOARD"}}},
                2,
            )

    _assert_tool_error(reserved, "CONFLICT", forbidden_path=fixture.root)
    _assert_tool_error(archived, "CONFLICT", forbidden_path=fixture.root)
    assert not (fixture.root / "kanban" / "boards" / "default").exists()
    assert not (fixture.root / "kanban" / "boards" / "archived-public-board").exists()


def test_beta_board_rename_unknown_slug_is_not_an_implicit_create(tmp_path, monkeypatch):
    asyncio.run(_test_beta_board_rename_unknown_slug_is_not_an_implicit_create(tmp_path, monkeypatch))


async def _test_beta_board_rename_unknown_slug_is_not_an_implicit_create(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    administrator = _token(
        auth,
        "rename-administrator",
        ["hermes:read", "hermes:create", "hermes:manage", "hermes:board:create", "hermes:admin"],
        board=fixture.board,
    )
    target = "unknown-rename-board"
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            before = tree_fingerprint(fixture.root)
            result = await _rpc(
                client,
                administrator,
                "tools/call",
                {
                    "name": "boards-rename",
                    "arguments": {"request": {"slug": target, "name": "Must Not Exist"}},
                },
            )
            after = tree_fingerprint(fixture.root)

    _assert_tool_error(result, "BOARD_NOT_FOUND", forbidden_path=fixture.root)
    assert after == before
    assert not (fixture.root / "kanban" / "boards" / target).exists()


def test_management_commands_are_global_on_beta_and_return_safe_errors(tmp_path, monkeypatch):
    asyncio.run(_test_management_commands_are_global_on_beta_and_return_safe_errors(tmp_path, monkeypatch))


async def _test_management_commands_are_global_on_beta_and_return_safe_errors(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    with kanban_db.connect_closing(db_path=fixture.db_path, board=fixture.board) as conn:
        conn.execute(
            "INSERT INTO tasks (id, title, status, claim_lock, created_at) VALUES (?, ?, ?, ?, ?)",
            ("running-task", "Running", "running", "claimed", 1_700_000_099),
        )
    other_db = fixture.root / "kanban" / "boards" / "other-board" / "kanban.db"
    with kanban_db.connect_closing(db_path=other_db, board="other-board") as conn:
        conn.execute(
            "INSERT INTO tasks (id, title, status, claim_lock, created_at) VALUES (?, ?, ?, ?, ?)",
            ("other-review", "Other Review", "review", None, 1_700_000_111),
        )
    manager = _token(auth, "manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _rpc(client, manager, "tools/call", {"name": "list_boards", "arguments": {}}, 0)
            before_cross = tree_fingerprint(fixture.root)
            cross_board = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "add_comment",
                    "arguments": {"request": {"board": "other-board", "task_id": "other-review", "body": "crossed board"}},
                },
                1,
            )
            after_cross = tree_fingerprint(fixture.root)
            missing = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "assign_task",
                    "arguments": {"request": {"board": fixture.board, "task_id": "missing-task", "assignee": "planner"}},
                },
                2,
            )
            conflict = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "assign_task",
                    "arguments": {"request": {"board": fixture.board, "task_id": "running-task", "assignee": "planner"}},
                },
                21,
            )
            commented = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "add_comment",
                    "arguments": {"request": {"board": fixture.board, "task_id": "review-task", "body": "MCP evidence"}},
                },
                3,
            )
            assigned = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "assign_task",
                    "arguments": {"request": {"board": fixture.board, "task_id": "review-task", "assignee": "planner"}},
                },
                4,
            )

    _assert_tool_error(missing, "TASK_NOT_FOUND", forbidden_path=fixture.root)
    _assert_tool_error(conflict, "CONFLICT", forbidden_path=fixture.root)
    _assert_tool_error(cross_board, "BOARD_SESSION_MISMATCH", forbidden_path=fixture.root)
    assert after_cross == before_cross
    assert commented["result"]["structuredContent"]["author"] == "chatgpt_mcp"
    assert commented["result"]["structuredContent"]["board"] == fixture.board
    assert assigned["result"]["structuredContent"] == {
        "board": fixture.board,
        "task_id": "review-task",
        "assignee": "planner",
        "status": "review",
    }


def test_update_task_is_idempotent_with_accurate_provenance(tmp_path, monkeypatch):
    asyncio.run(_test_update_task_is_idempotent_with_accurate_provenance(tmp_path, monkeypatch))


async def _test_update_task_is_idempotent_with_accurate_provenance(tmp_path, monkeypatch):
    """Retrying the same update_task call succeeds without new writes.

    The first call reports only the fields the canonical primitive actually
    changed (a before/after state diff, not merely the requested ones); the
    exact replay is an idempotent success reported with empty updated_fields,
    and a partial-field replay reports only the field that still differed.
    Neither replay persists anything new. Missing tasks still surface as
    TASK_NOT_FOUND.
    """
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    manager = _token(auth, "updater", ["hermes:read", "hermes:manage"], board=fixture.board)
    arguments = {
        "request": {
            "board": fixture.board,
            "task_id": "review-task",
            "title": "Renamed review",
            "priority": 9,
        }
    }
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            first = await _rpc(client, manager, "tools/call", {"name": "update_task", "arguments": dict(arguments)}, 1)
            second = await _rpc(client, manager, "tools/call", {"name": "update_task", "arguments": dict(arguments)}, 2)
            partial = await _rpc(
                client,
                manager,
                "tools/call",
                {"name": "update_task", "arguments": {"request": {"board": fixture.board, "task_id": "review-task", "title": "Renamed review", "priority": 2}}},
                3,
            )
            missing = await _rpc(
                client,
                manager,
                "tools/call",
                {"name": "update_task", "arguments": {"request": {"board": fixture.board, "task_id": "missing-task", "title": "x"}}},
                4,
            )

    assert first["result"]["isError"] is False
    assert first["result"]["structuredContent"] == {
        "board": fixture.board,
        "task_id": "review-task",
        "updated_fields": ["title", "priority"],
    }
    assert second["result"]["isError"] is False
    assert second["result"]["structuredContent"] == {
        "board": fixture.board,
        "task_id": "review-task",
        "updated_fields": [],
    }
    # A partial-field replay (one value already applied, one differing) is
    # still idempotent success and reports only the field that changed.
    assert partial["result"]["isError"] is False
    assert partial["result"]["structuredContent"] == {
        "board": fixture.board,
        "task_id": "review-task",
        "updated_fields": ["priority"],
    }

    with kanban_db.connect_closing(db_path=fixture.db_path, board=fixture.board) as conn:
        task = kanban_db.get_task(conn, "review-task")
        assert task.title == "Renamed review"
        assert task.priority == 2
        comments = [item.body for item in kanban_db.list_comments(conn, "review-task")]
        # one provenance comment per real write — neither replay wrote one
        assert sum("Edited — updated" in body for body in comments) == 2
        edits = [event for event in kanban_db.list_events(conn, "review-task") if event.kind == "edited_fields"]
        assert len(edits) == 2
        assert edits[0].payload["changed_fields"] == ["title", "priority"]
        assert edits[1].payload["changed_fields"] == ["priority"]
        for edit in edits:
            assert edit.payload["by"] == "chatgpt_mcp"

    _assert_tool_error(missing, "TASK_NOT_FOUND", forbidden_path=fixture.root)


def test_notify_subscribe_rejects_unknown_delivery_mode(tmp_path, monkeypatch):
    asyncio.run(_test_notify_subscribe_rejects_unknown_delivery_mode(tmp_path, monkeypatch))


async def _test_notify_subscribe_rejects_unknown_delivery_mode(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    manager = _token(auth, "notify-manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            before = tree_fingerprint(fixture.root)
            invalid = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "notify-subscribe",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "task_id": "review-task",
                            "platform": "qa",
                            "chat_id": "invalid-delivery",
                            "delivery": "test",
                        }
                    },
                },
            )
            after = tree_fingerprint(fixture.root)

    assert invalid["result"]["isError"] is True
    assert "notify" in str(invalid)
    assert "Traceback" not in str(invalid)
    assert after == before


def test_notify_subscribe_preserves_supported_delivery_mode(tmp_path, monkeypatch):
    asyncio.run(_test_notify_subscribe_preserves_supported_delivery_mode(tmp_path, monkeypatch))


async def _test_notify_subscribe_preserves_supported_delivery_mode(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    manager = _token(auth, "notify-roundtrip", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            subscribed = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "notify-subscribe",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "task_id": "review-task",
                            "platform": "qa",
                            "chat_id": "supported-delivery",
                            "delivery": "wake",
                        }
                    },
                },
            )
            listed = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "notify-list",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "task_id": "review-task",
                            "limit": 5,
                        }
                    },
                },
                2,
            )
            await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "notify-unsubscribe",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "task_id": "review-task",
                            "platform": "qa",
                            "chat_id": "supported-delivery",
                        }
                    },
                },
                3,
            )

    assert subscribed["result"]["structuredContent"]["delivery"] == "wake"
    assert listed["result"]["structuredContent"]["subscriptions"] == [
        {
            "task_id": "review-task",
            "platform": "qa",
            "chat_id": "supported-delivery",
            "thread_id": None,
            "delivery": "wake",
        }
    ]


def test_beta_scope_matrix_denies_only_the_unauthorized_mutations(tmp_path, monkeypatch):
    asyncio.run(_test_beta_scope_matrix_denies_only_the_unauthorized_mutations(tmp_path, monkeypatch))


async def _test_beta_scope_matrix_denies_only_the_unauthorized_mutations(tmp_path, monkeypatch):
    fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
    reader = _token(auth, "matrix-reader", ["hermes:read"])
    creator = _token(auth, "matrix-creator", ["hermes:read", "hermes:create"], board=fixture.board)
    manager = _token(auth, "matrix-manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    administrator = _token(auth, "matrix-administrator", ["hermes:read", "hermes:board:create"])
    combined = _token(
        auth,
        "matrix-combined",
        ["hermes:read", "hermes:create", "hermes:manage"],
        board=fixture.board,
    )
    denied_calls = [
        (reader, "create_task", {"request": {"board": fixture.board, "title": "denied", "idempotency_key": "matrix-read-1"}}),
        (reader, "create_board", {"request": {"slug": "matrix-read-board"}}),
        (reader, "add_comment", {"request": {"board": fixture.board, "task_id": "review-task", "body": "denied"}}),
        (reader, "assign_task", {"request": {"board": fixture.board, "task_id": "review-task", "assignee": "planner"}}),
        (creator, "create_board", {"request": {"slug": "matrix-create-board"}}),
        (creator, "add_comment", {"request": {"board": fixture.board, "task_id": "review-task", "body": "denied"}}),
        (creator, "assign_task", {"request": {"board": fixture.board, "task_id": "review-task", "assignee": "planner"}}),
        (manager, "create_board", {"request": {"slug": "matrix-manage-board"}}),
        (administrator, "create_task", {"request": {"board": fixture.board, "title": "denied", "idempotency_key": "matrix-admin-1"}}),
        (manager, "create_task", {"request": {"board": fixture.board, "title": "denied", "idempotency_key": "matrix-manage-1"}}),
    ]
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _rpc(client, reader, "tools/call", {"name": "list_boards", "arguments": {}}, 0)
            before = tree_fingerprint(fixture.root)
            results = [
                await _rpc(
                    client,
                    token,
                    "tools/call",
                    {"name": name, "arguments": arguments},
                    request_id,
                )
                for request_id, (token, name, arguments) in enumerate(denied_calls, start=1)
            ]
            after_denials = tree_fingerprint(fixture.root)
            allowed = await _rpc(
                client,
                combined,
                "tools/call",
                {
                    "name": "create_task",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "title": "manage plus create",
                            "idempotency_key": "matrix-combined-1",
                        }
                    },
                },
                20,
            )

    for result in results:
        _assert_tool_error(result, "SCOPE_REQUIRED", forbidden_path=fixture.root)
    assert after_denials == before
    assert allowed["result"].get("isError") is not True
    assert allowed["result"]["structuredContent"]["board"] == fixture.board
