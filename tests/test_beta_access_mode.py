from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx

from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.boards import HermesBoardResolver
from hermes_chatgpt_mcp.server import create_app

from hermes_cli import kanban_db

from .fixtures import make_hermes_fixture
from .test_auth import _settings


def _pkce(suffix: str) -> tuple[str, str]:
    verifier = "verifier-" + suffix * 30
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _beta_app(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    kanban_db.set_current_board(fixture.board)
    kanban_db.create_board("admin-probe", name="Admin Probe")
    settings = replace(
        _settings(),
        hermes_kanban_home=fixture.root,
        default_board=fixture.board,
        kanban_read_boards=None,
        kanban_create_boards=None,
        oauth_state_file=tmp_path / "beta-access-mode-state.json",
        surface="beta",
        board_create_enabled=True,
    )
    auth = AuthService(settings)
    resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")
    return fixture, settings, auth, app


def _register(client, callback, scope):
    return {
        "client_name": "ChatGPT beta access mode",
        "redirect_uris": [callback],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": scope,
    }


def _all_scopes() -> str:
    return "hermes:read hermes:create hermes:manage hermes:board:create hermes:admin offline_access"


def test_beta_all_scopes_read_strips_command_scopes_and_stays_global(tmp_path, monkeypatch):
    asyncio.run(_test_beta_all_scopes_read_strips_command_scopes_and_stays_global(tmp_path, monkeypatch))


def test_beta_all_scopes_write_resolves_board_and_retains_admin(tmp_path, monkeypatch):
    asyncio.run(_test_beta_all_scopes_write_resolves_board_and_retains_admin(tmp_path, monkeypatch))


def test_beta_write_without_command_scope_is_denied(tmp_path, monkeypatch):
    asyncio.run(_test_beta_write_without_command_scope_is_denied(tmp_path, monkeypatch))


def test_beta_omitted_access_mode_defaults_to_read_and_strips_command_scopes(tmp_path, monkeypatch):
    asyncio.run(_test_beta_omitted_access_mode_defaults_to_read_and_strips_command_scopes(tmp_path, monkeypatch))


async def _test_beta_all_scopes_read_strips_command_scopes_and_stays_global(tmp_path, monkeypatch):
    fixture, settings, auth, app = _beta_app(tmp_path, monkeypatch)
    callback = "https://chatgpt.com/connector/oauth/callback"
    verifier, challenge = _pkce("a")
    scope = _all_scopes()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json=_register(client, callback, scope))
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": scope,
                "state": "all-scopes-read",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            approved = await client.post(
                "/oauth/authorize",
                data={
                    **params,
                    "username": "chatgpt",
                    "password": "correct horse battery staple",
                    "access_mode": "read",
                },
            )
            assert approved.status_code == 303, approved.text
            code = parse_qs(urlsplit(approved.headers["location"]).query)["code"][0]
            token = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_data["client_id"],
                    "code": code,
                    "redirect_uri": callback,
                    "code_verifier": verifier,
                },
            )
            assert token.status_code == 200, token.text
            granted = token.json()["scope"].split()
            assert "hermes:create" not in granted
            assert "hermes:manage" not in granted
            assert "hermes:read" in granted
            assert "hermes:board:create" in granted
            assert "hermes:admin" in granted
            assert "offline_access" in granted
            claims = auth.verified_claims(token.json()["access_token"])
            assert claims is not None
            assert "board" not in claims
            assert "board_access" not in claims


async def _test_beta_all_scopes_write_resolves_board_and_retains_admin(tmp_path, monkeypatch):
    fixture, settings, auth, app = _beta_app(tmp_path, monkeypatch)
    callback = "https://chatgpt.com/connector/oauth/callback"
    verifier, challenge = _pkce("b")
    scope = _all_scopes()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json=_register(client, callback, scope))
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": scope,
                "state": "all-scopes-write",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            approved = await client.post(
                "/oauth/authorize",
                data={
                    **params,
                    "username": "chatgpt",
                    "password": "correct horse battery staple",
                    "access_mode": "write",
                    "board": fixture.board,
                },
            )
            assert approved.status_code == 303, approved.text
            code = parse_qs(urlsplit(approved.headers["location"]).query)["code"][0]
            token = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_data["client_id"],
                    "code": code,
                    "redirect_uri": callback,
                    "code_verifier": verifier,
                },
            )
            assert token.status_code == 200, token.text
            body = token.json()
            granted = body["scope"].split()
            assert "hermes:create" in granted
            assert "hermes:manage" in granted
            assert "hermes:board:create" in granted
            assert "hermes:admin" in granted
            claims = auth.verified_claims(body["access_token"])
            assert claims is not None
            assert claims["board"] == fixture.board
            assert claims["board_access"] == "write"


async def _test_beta_write_without_command_scope_is_denied(tmp_path, monkeypatch):
    fixture, settings, auth, app = _beta_app(tmp_path, monkeypatch)
    callback = "https://chatgpt.com/connector/oauth/callback"
    verifier, challenge = _pkce("c")
    # A client that only requested read+board:create (no task/card command scope).
    scope = "hermes:read hermes:board:create hermes:admin offline_access"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json=_register(client, callback, scope))
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": scope,
                "state": "write-no-command",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            approved = await client.post(
                "/oauth/authorize",
                data={
                    **params,
                    "username": "chatgpt",
                    "password": "correct horse battery staple",
                    "access_mode": "write",
                    "board": fixture.board,
                },
            )
            assert approved.status_code == 400, approved.text
            assert "invalid_scope" in approved.text


async def _test_beta_omitted_access_mode_defaults_to_read_and_strips_command_scopes(tmp_path, monkeypatch):
    fixture, settings, auth, app = _beta_app(tmp_path, monkeypatch)
    callback = "https://chatgpt.com/connector/oauth/callback"
    verifier, challenge = _pkce("d")
    scope = _all_scopes()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json=_register(client, callback, scope))
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": scope,
                "state": "omitted-access-mode",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            approved = await client.post(
                "/oauth/authorize",
                data={
                    **params,
                    "username": "chatgpt",
                    "password": "correct horse battery staple",
                    # access_mode deliberately omitted -> defaults to read.
                },
            )
            assert approved.status_code == 303, approved.text
            code = parse_qs(urlsplit(approved.headers["location"]).query)["code"][0]
            token = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_data["client_id"],
                    "code": code,
                    "redirect_uri": callback,
                    "code_verifier": verifier,
                },
            )
            assert token.status_code == 200, token.text
            granted = token.json()["scope"].split()
            assert "hermes:create" not in granted
            assert "hermes:manage" not in granted
            claims = auth.verified_claims(token.json()["access_token"])
            assert claims is not None
            assert "board" not in claims
            assert "board_access" not in claims
