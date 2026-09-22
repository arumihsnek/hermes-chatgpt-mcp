"""R0 authorization-boundary regression tests (read-only investigation artifact).

Covers the two confirmed findings:
  F1 (t_ffd2cbe8): beta resolve_board skipped the board-bound write-grant
      check for holders of hermes:admin, so create_task succeeded on boards
      advertised CREATE=false.
  F2 (R0/D4): OAuth read-mode consent retained hermes:board:create, so a
      "read-only" grant announced global create_board=true.

All tests run against an isolated fixture (tmp HOME/DB); no services,
no credentials, no production boards.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.boards import HermesBoardResolver
from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.server import create_app

from hermes_cli import kanban_db

from .test_auth import _settings
from .test_boards import _write_board
from .test_mcp_multiboard import _rpc, _seed_task


def _beta_settings(root: Path) -> Settings:
    return replace(
        _settings(),
        hermes_kanban_home=root,
        default_board="board-a",
        kanban_read_boards=None,
        kanban_create_boards=None,
        surface="beta",
        board_create_enabled=True,
        oauth_state_file=root / "beta-oauth-state.json",
    )


def _make_beta_app(tmp_path: Path, monkeypatch):
    _write_board(tmp_path, "board-a", name="Board A")
    _write_board(tmp_path, "board-b", name="Board B")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    task_a_id = _seed_task(tmp_path, "board-a", "seed-a", "A-only task")
    task_b_id = _seed_task(tmp_path, "board-b", "seed-b", "B-only task")
    settings = _beta_settings(tmp_path)
    auth = AuthService(settings)
    resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")
    return settings, auth, app, task_a_id, task_b_id


def _admin_create_token(auth: AuthService) -> str:
    # Admin + command grant is itself board-bound per docs/SECURITY.md.
    return auth.issue_access_token(
        client_id="admin-creator",
        subject="admin-creator",
        scopes=["hermes:read", "hermes:create", "hermes:admin"],
        board="board-a",
        board_access="write",
    )


async def _test_admin_grant_bound_to_a_cannot_write_b(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_beta_app(tmp_path, monkeypatch)
    token = _admin_create_token(auth)
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
                    "board": "board-b", "title": "admin cross-board must be rejected",
                    "idempotency_key": "r0-admin-b-denied-1",
                }}}, 2,
            )
            after = await _rpc(
                client, token, "tools/call",
                {"name": "list_tasks", "arguments": {"request": {"board": "board-b", "limit": 20}}}, 3,
            )
    assert rejected["result"]["isError"] is True
    assert "BOARD_SESSION_MISMATCH" in str(rejected)
    assert after["result"]["structuredContent"]["items"] == before["result"]["structuredContent"]["items"]


def test_admin_grant_bound_to_a_cannot_write_b(tmp_path, monkeypatch):
    asyncio.run(_test_admin_grant_bound_to_a_cannot_write_b(tmp_path, monkeypatch))


async def _test_admin_grant_bound_to_a_can_write_a(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_beta_app(tmp_path, monkeypatch)
    token = _admin_create_token(auth)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            created = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "board": "board-a", "title": "admin same-board allowed",
                    "idempotency_key": "r0-admin-a-allowed-1",
                }}}, 1,
            )
    payload = created["result"]["structuredContent"]
    assert created["result"]["isError"] is not True
    assert payload["board"] == "board-a"


def test_admin_grant_bound_to_a_can_write_a(tmp_path, monkeypatch):
    asyncio.run(_test_admin_grant_bound_to_a_can_write_a(tmp_path, monkeypatch))


async def _test_admin_manage_grant_bound_to_a_cannot_comment_on_b(tmp_path, monkeypatch):
    settings, auth, app, _, task_b_id = _make_beta_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(
        client_id="admin-manager",
        subject="admin-manager",
        scopes=["hermes:read", "hermes:manage", "hermes:admin"],
        board="board-a",
        board_access="write",
    )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            rejected = await _rpc(
                client, token, "tools/call",
                {"name": "add_comment", "arguments": {"request": {
                    "board": "board-b", "task_id": task_b_id, "body": "must be rejected",
                }}}, 1,
            )
            comments = await _rpc(
                client, token, "tools/call",
                {"name": "get_task", "arguments": {"request": {"board": "board-b", "task_id": task_b_id}}}, 2,
            )
    assert rejected["result"]["isError"] is True
    assert "BOARD_SESSION_MISMATCH" in str(rejected)
    assert "must be rejected" not in str(comments)


def test_admin_manage_grant_bound_to_a_cannot_comment_on_b(tmp_path, monkeypatch):
    asyncio.run(_test_admin_manage_grant_bound_to_a_cannot_comment_on_b(tmp_path, monkeypatch))


async def _test_omitted_board_resolves_to_grant_board(tmp_path, monkeypatch):
    settings, auth, app, _, _ = _make_beta_app(tmp_path, monkeypatch)
    token = auth.issue_access_token(
        client_id="creator",
        subject="creator",
        scopes=["hermes:read", "hermes:create"],
        board="board-a",
        board_access="write",
    )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            created = await _rpc(
                client, token, "tools/call",
                {"name": "create_task", "arguments": {"request": {
                    "title": "omitted board lands on grant board",
                    "idempotency_key": "r0-omitted-board-1",
                }}}, 1,
            )
    assert created["result"]["structuredContent"]["board"] == "board-a"


def test_omitted_board_resolves_to_grant_board(tmp_path, monkeypatch):
    asyncio.run(_test_omitted_board_resolves_to_grant_board(tmp_path, monkeypatch))


async def _test_read_consent_strips_board_create_scope(tmp_path, monkeypatch):
    from .fixtures import make_hermes_fixture

    fixture = make_hermes_fixture(tmp_path / "fixture")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    settings = replace(
        _settings(),
        hermes_kanban_home=fixture.root,
        default_board=fixture.board,
        kanban_read_boards=None,
        kanban_create_boards=None,
        oauth_state_file=tmp_path / "r0-oauth-state.json",
        surface="beta",
        board_create_enabled=True,
    )
    auth = AuthService(settings)
    resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")
    verifier = "r0-verifier-" + "e" * 32
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    callback = "https://chatgpt.com/connector/oauth/callback"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json={
                "client_name": "R0 fixture client",
                "redirect_uris": [callback],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "hermes:read hermes:board:create",
            })
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": "hermes:read hermes:board:create",
                "state": "state-r0",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            approved = await client.post("/oauth/authorize", data={
                **params,
                "username": "chatgpt",
                "password": "correct horse battery staple",
                "access_mode": "read",
            })
            assert approved.status_code == 303, approved.text
            code = parse_qs(urlsplit(approved.headers["location"]).query)["code"][0]
            token = await client.post("/oauth/token", data={
                "grant_type": "authorization_code",
                "client_id": client_data["client_id"],
                "code": code,
                "redirect_uri": callback,
                "code_verifier": verifier,
            })
    assert token.status_code == 200, token.text
    assert token.json()["scope"] == "hermes:read"


def test_read_consent_strips_board_create_scope(tmp_path, monkeypatch):
    asyncio.run(_test_read_consent_strips_board_create_scope(tmp_path, monkeypatch))
