from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import httpx

from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.boards import HermesBoardResolver
from hermes_chatgpt_mcp.command import HermesBoardAdminAdapter, HermesCreateAdapter
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app

from hermes_cli import kanban_db

from .fixtures import make_hermes_fixture, tree_fingerprint
from .test_auth import _settings


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
    assert response.status_code == 200
    return response.json()


def _beta_fixture(tmp_path: Path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    kanban_db.set_current_board(fixture.board)

    board_b = HermesBoardAdminAdapter(kanban_db).create_board(
        "fixture-board-b",
        name="Fixture Board B",
        description="Second canonical beta fixture board",
    )

    settings = replace(
        _settings(),
        hermes_kanban_home=fixture.root,
        default_board=fixture.board,
        kanban_read_boards=None,
        kanban_create_boards=None,
        oauth_state_file=tmp_path / "beta-oauth-state.json",
        surface="beta",
        board_create_enabled=True,
    )
    auth = AuthService(settings)
    resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    app = create_app(
        board_resolver=resolver,
        settings=settings,
        auth_service=auth,
        surface="beta",
    )
    return fixture, board_b, settings, auth, app


def _token(auth: AuthService, client_id: str, scopes: list[str], *, board: str | None = None) -> str:
    return auth.issue_access_token(
        client_id=client_id,
        subject=client_id,
        scopes=scopes,
        board=board,
        board_access="write" if board else None,
    )


def _canonical_board_store(fixture, board: str) -> ReadOnlyHermesStore:
    return ReadOnlyHermesStore(
        db_path=ReadOnlyHermesStore.resolve_board_path(fixture.root, board),
        board=board,
        hermes_module=kanban_db,
        hermes_agent_root=fixture.root,
        log_root=fixture.root / "kanban" / "boards" / board / "logs",
    )


def _assert_error(result: dict, code: str) -> None:
    payload = result["result"]
    assert payload["isError"] is True
    rendered = " ".join(str(item.get("text", "")) for item in payload.get("content", []))
    assert f'"code":"{code}"' in rendered
    assert "Traceback" not in rendered
    assert "stack" not in rendered.lower()


def _assert_success(result: dict) -> dict:
    payload = result["result"]
    assert payload.get("isError") is not True
    return payload["structuredContent"]


async def _read_all(client: httpx.AsyncClient, token: str, board: str) -> None:
    calls = [
        ("list_boards", {}),
        ("get_board", {"request": {"board": board}}),
        ("list_tasks", {"request": {"board": board, "limit": 20, "include_archived": True}}),
        ("get_task", {"request": {"board": board, "task_id": "review-task"}}),
        ("get_task_graph", {"request": {"board": board, "task_id": "child-ready", "depth": 1, "max_nodes": 10}}),
        ("get_dispatch", {"request": {"board": board, "task_id": "child-blocked"}}),
        ("get_activity", {"request": {"board": board, "task_id": "review-task", "max_items": 20, "log_bytes": 1000}}),
    ]
    for request_id, (name, arguments) in enumerate(calls, start=1):
        result = await _rpc(
            client,
            token,
            "tools/call",
            {"name": name, "arguments": arguments},
            request_id,
        )
        _assert_success(result)


def test_beta_create_board_dogfood_is_canonical_and_idempotent(tmp_path, monkeypatch):
    asyncio.run(_test_beta_create_board_dogfood_is_canonical_and_idempotent(tmp_path, monkeypatch))


async def _test_beta_create_board_dogfood_is_canonical_and_idempotent(tmp_path, monkeypatch):
    fixture, board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    administrator = _token(auth, "board-administrator", ["hermes:read", "hermes:board:create"])
    current_before = kanban_db.get_current_board()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            before = _assert_success(
                await _rpc(client, administrator, "tools/call", {"name": "list_boards", "arguments": {}}, 1)
            )
            first = _assert_success(
                await _rpc(
                    client,
                    administrator,
                    "tools/call",
                    {
                        "name": "create_board",
                        "arguments": {
                            "request": {
                                "slug": "beta-dogfood-board",
                                "name": "Beta Dogfood Board",
                                "description": "Temporary beta fixture board",
                                "icon": "beta",
                                "color": "#336699",
                            }
                        },
                    },
                    2,
                )
            )
            repeated = _assert_success(
                await _rpc(
                    client,
                    administrator,
                    "tools/call",
                    {
                        "name": "create_board",
                        "arguments": {
                            "request": {
                                "slug": "beta-dogfood-board",
                                "name": "Conflicting Metadata",
                                "description": "Must not replace canonical metadata",
                                "icon": "conflict",
                                "color": "#ff0000",
                            }
                        },
                    },
                    3,
                )
            )
            after = _assert_success(
                await _rpc(client, administrator, "tools/call", {"name": "list_boards", "arguments": {}}, 4)
            )

    assert [item["slug"] for item in before["items"]] == [fixture.board, board_b.slug]
    assert first == repeated == {
        "slug": "beta-dogfood-board",
        "name": "Beta Dogfood Board",
        "description": "Temporary beta fixture board",
        "icon": "beta",
        "color": "#336699",
        "created": True,
        "is_default": False,
    }
    assert [item["slug"] for item in after["items"]].count("beta-dogfood-board") == 1
    assert len(after["items"]) == len(before["items"]) + 1
    assert after["default_board"] == fixture.board
    assert next(item for item in after["items"] if item["slug"] == "beta-dogfood-board")["is_default"] is False
    assert kanban_db.get_current_board() == current_before == fixture.board


def test_beta_selected_board_management_and_canonical_activity(tmp_path, monkeypatch):
    asyncio.run(_test_beta_selected_board_management_and_canonical_activity(tmp_path, monkeypatch))


def test_beta_create_board_case_variant_preserves_canonical_metadata(tmp_path, monkeypatch):
    asyncio.run(_test_beta_create_board_case_variant_preserves_canonical_metadata(tmp_path, monkeypatch))


async def _test_beta_create_board_case_variant_preserves_canonical_metadata(tmp_path, monkeypatch):
    fixture, board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    administrator = _token(auth, "case-variant-administrator", ["hermes:read", "hermes:board:create"])
    current_before = kanban_db.get_current_board()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            first = _assert_success(
                await _rpc(
                    client,
                    administrator,
                    "tools/call",
                    {
                        "name": "create_board",
                        "arguments": {
                            "request": {
                                "slug": "case-board",
                                "name": "Case Canonical Board",
                                "description": "Canonical case-insensitive board",
                                "icon": "case",
                                "color": "#123456",
                            }
                        },
                    },
                    1,
                )
            )
            repeated = _assert_success(
                await _rpc(
                    client,
                    administrator,
                    "tools/call",
                    {
                        "name": "create_board",
                        "arguments": {
                            "request": {
                                "slug": "CASE-BOARD",
                                "name": "Conflicting Case Metadata",
                                "description": "Must not replace the canonical case variant",
                                "icon": "conflict",
                                "color": "#abcdef",
                            }
                        },
                    },
                    2,
                )
            )
            boards = _assert_success(
                await _rpc(client, administrator, "tools/call", {"name": "list_boards", "arguments": {}}, 3)
            )

    assert first == repeated == {
        "slug": "case-board",
        "name": "Case Canonical Board",
        "description": "Canonical case-insensitive board",
        "icon": "case",
        "color": "#123456",
        "created": True,
        "is_default": False,
    }
    assert [item["slug"] for item in boards["items"]].count("case-board") == 1
    assert kanban_db.get_current_board() == current_before == fixture.board


async def _test_beta_selected_board_management_and_canonical_activity(tmp_path, monkeypatch):
    fixture, board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    board_b_task = HermesCreateAdapter(_canonical_board_store(fixture, board_b.slug)).create_task(
        title="Board B known task",
        body="Canonical Board B seed for isolation coverage",
        idempotency_key="board-b-known-task-1",
    )
    board_b_queries = HermesReadOnlyAdapter(_canonical_board_store(fixture, board_b.slug))
    board_b_before_task = board_b_queries.get_task(board_b_task.task_id).model_dump()
    board_b_before_activity = board_b_queries.get_activity(
        board_b_task.task_id,
        max_items=50,
        log_bytes=0,
    ).model_dump()
    assert board_b_before_task["title"] == "Board B known task"
    assert board_b_before_task["created_by"] == "chatgpt_mcp"
    assert kanban_db.get_current_board() == fixture.board
    creator = _token(auth, "creator", ["hermes:read", "hermes:create"], board=fixture.board)
    manager = _token(auth, "manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            created = _assert_success(
                await _rpc(
                    client,
                    creator,
                    "tools/call",
                    {
                        "name": "create_task",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "title": "Beta dogfood card",
                                "body": "Canonical beta integration card",
                                "idempotency_key": "beta-dogfood-card-1",
                            }
                        },
                    },
                    1,
                )
            )
            commented = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "add_comment",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "task_id": "review-task",
                                "body": "Beta integration evidence",
                            }
                        },
                    },
                    2,
                )
            )
            assigned = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "assign_task",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "task_id": "review-task",
                                "assignee": "planner",
                            }
                        },
                    },
                    3,
                )
            )
            review_activity = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "get_activity",
                        "arguments": {"request": {"board": fixture.board, "task_id": "review-task", "max_items": 50, "log_bytes": 0}},
                    },
                    4,
                )
            )
            created_activity = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "get_activity",
                        "arguments": {"request": {"board": fixture.board, "task_id": created["task_id"], "max_items": 50, "log_bytes": 0}},
                    },
                    5,
                )
            )

            before_denied_board = tree_fingerprint(fixture.root)
            wrong_comment = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "add_comment",
                    "arguments": {"request": {"board": board_b.slug, "task_id": board_b_task.task_id, "body": "must not cross boards"}},
                },
                6,
            )
            wrong_assignment = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "assign_task",
                    "arguments": {"request": {"board": board_b.slug, "task_id": board_b_task.task_id, "assignee": "planner"}},
                },
                7,
            )
            board_b_after_task = board_b_queries.get_task(board_b_task.task_id).model_dump()
            board_b_after_activity = board_b_queries.get_activity(
                board_b_task.task_id,
                max_items=50,
                log_bytes=0,
            ).model_dump()
            after_denied_board = tree_fingerprint(fixture.root)

    assert created["board"] == fixture.board
    assert commented["author"] == "chatgpt_mcp"
    assert assigned == {"board": fixture.board, "task_id": "review-task", "assignee": "planner", "status": "review"}
    assert "created" in {event["kind"] for event in created_activity["events"]}
    assert {"commented", "assigned"}.issubset({event["kind"] for event in review_activity["events"]})
    # Beta surface (2026-08-18): card writes are GLOBAL across boards, so a
    # board-scoped token may also manage the second canonical board.
    assert wrong_comment["result"].get("isError") is not True, wrong_comment
    assert wrong_comment["result"]["structuredContent"]["board"] == board_b.slug
    assert wrong_comment["result"]["structuredContent"]["author"] == "chatgpt_mcp"
    assert wrong_assignment["result"].get("isError") is not True, wrong_assignment
    assert board_b_after_task["assignee"] == "planner"
    assert {"commented", "assigned"}.issubset({event["kind"] for event in board_b_after_activity["events"]})
    assert after_denied_board != before_denied_board


def test_beta_read_tools_and_scope_denials_preserve_fixture_fingerprint(tmp_path, monkeypatch):
    asyncio.run(_test_beta_read_tools_and_scope_denials_preserve_fixture_fingerprint(tmp_path, monkeypatch))


async def _test_beta_read_tools_and_scope_denials_preserve_fixture_fingerprint(tmp_path, monkeypatch):
    fixture, _, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    reader = _token(auth, "reader", ["hermes:read"])
    creator = _token(auth, "creator", ["hermes:read", "hermes:create"], board=fixture.board)
    manager = _token(auth, "manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    administrator = _token(auth, "administrator", ["hermes:read", "hermes:board:create"])
    combined = _token(auth, "combined", ["hermes:read", "hermes:create", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            await _read_all(client, reader, fixture.board)
            before_reads = tree_fingerprint(fixture.root)
            await _read_all(client, reader, fixture.board)
            after_reads = tree_fingerprint(fixture.root)

            denied = [
                (reader, "create_task", {"request": {"board": fixture.board, "title": "read denied", "idempotency_key": "read-denied-1"}}, 10),
                (reader, "create_board", {"request": {"slug": "read-denied-board"}}, 11),
                (reader, "add_comment", {"request": {"board": fixture.board, "task_id": "review-task", "body": "read denied"}}, 12),
                (reader, "assign_task", {"request": {"board": fixture.board, "task_id": "review-task", "assignee": "planner"}}, 13),
                (creator, "create_board", {"request": {"slug": "create-denied-board"}}, 14),
                (administrator, "create_task", {"request": {"board": fixture.board, "title": "admin denied", "idempotency_key": "admin-denied-1"}}, 15),
                (administrator, "add_comment", {"request": {"board": fixture.board, "task_id": "review-task", "body": "admin denied"}}, 16),
                (manager, "create_task", {"request": {"board": fixture.board, "title": "manage denied", "idempotency_key": "manage-denied-1"}}, 17),
            ]
            denied_results = [
                await _rpc(client, token, "tools/call", {"name": name, "arguments": arguments}, request_id)
                for token, name, arguments, request_id in denied
            ]
            after_denials = tree_fingerprint(fixture.root)

            allowed_with_both = _assert_success(
                await _rpc(
                    client,
                    combined,
                    "tools/call",
                    {
                        "name": "create_task",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "title": "manage plus create allowed",
                                "idempotency_key": "manage-plus-create-1",
                            }
                        },
                    },
                    18,
                )
            )

    assert after_reads == before_reads
    assert after_denials == after_reads
    for result in denied_results:
        _assert_error(result, "SCOPE_REQUIRED")
    assert allowed_with_both["board"] == fixture.board


def test_beta_admin_token_can_create_board_and_work_in_it(tmp_path, monkeypatch):
    asyncio.run(_test_beta_admin_token_can_create_board_and_work_in_it(tmp_path, monkeypatch))


async def _test_beta_admin_token_can_create_board_and_work_in_it(tmp_path, monkeypatch):
    fixture, _, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    admin = _token(
        auth,
        "admin-global",
        ["hermes:read", "hermes:create", "hermes:manage", "hermes:board:create"],
    )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            created = _assert_success(
                await _rpc(
                    client, admin, "tools/call",
                    {"name": "create_board", "arguments": {"request": {
                        "slug": "admin-probe", "name": "Admin Probe",
                        "icon": "🧪", "color": "blue",
                    }}},
                    1,
                )
            )
            assert created["slug"] == "admin-probe"

            task = _assert_success(
                await _rpc(
                    client, admin, "tools/call",
                    {"name": "create_task", "arguments": {"request": {
                        "board": "admin-probe", "title": "first card",
                        "body": "created by the same admin token that made the board",
                        "idempotency_key": "admin-probe-1",
                    }}},
                    2,
                )
            )
            assert task["board"] == "admin-probe"
            task_id = task["task_id"]

            comment = await _rpc(
                client, admin, "tools/call",
                {"name": "add_comment", "arguments": {"request": {
                    "board": "admin-probe", "task_id": task_id, "body": "global admin comment",
                }}},
                3,
            )
            assert comment["result"].get("isError") is not True, comment

            assigned = await _rpc(
                client, admin, "tools/call",
                {"name": "assign_task", "arguments": {"request": {
                    "board": "admin-probe", "task_id": task_id, "assignee": "planner",
                }}},
                4,
            )
            assert assigned["result"].get("isError") is not True, assigned

            view = await _rpc(
                client, admin, "tools/call",
                {"name": "get_board", "arguments": {"request": {"board": "admin-probe"}}},
                5,
            )
            caps = view["result"]["structuredContent"]["capabilities"]
            assert caps["read"] is True and caps["create"] is True and caps["manage"] is True
