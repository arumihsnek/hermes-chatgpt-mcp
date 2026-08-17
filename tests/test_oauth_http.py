from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService, OAuthError
from hermes_chatgpt_mcp.boards import HermesBoardResolver
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.server import create_app

from hermes_cli import kanban_db

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


def test_oauth_http_pkce_flow_and_refresh_rotation(tmp_path):
    asyncio.run(_test_oauth_http_pkce_flow_and_refresh_rotation(tmp_path))


def test_oauth_http_dcr_default_then_create_authorization(tmp_path):
    asyncio.run(_test_oauth_http_dcr_default_then_create_authorization(tmp_path))


def test_oauth_http_read_choice_strips_create_and_is_global(tmp_path):
    asyncio.run(_test_oauth_http_read_choice_strips_create_and_is_global(tmp_path))


def test_beta_oauth_state_survives_fresh_service_and_isolated_from_stable(tmp_path, monkeypatch):
    asyncio.run(_test_beta_oauth_state_survives_fresh_service_and_isolated_from_stable(tmp_path, monkeypatch))


async def _test_oauth_http_dcr_default_then_create_authorization(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    app = create_app(_adapter(fixture), settings=settings, auth_service=AuthService(settings))
    verifier = "verifier-" + "b" * 35
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    callback = "https://chatgpt.com/connector/oauth/callback"
    requested_scope = "hermes:read hermes:create offline_access"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json={
                "client_name": "ChatGPT",
                "redirect_uris": [callback],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            })
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            assert client_data["scope"] == "hermes:read hermes:create"

            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": requested_scope,
                "state": "state-create",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            authorize = await client.get("/oauth/authorize", params=params)
            assert authorize.status_code == 200
            assert "Fixture Board" in authorize.text
            assert "Read all boards and write one selected board" in authorize.text

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
            assert approved.status_code == 303
            code = parse_qs(urlsplit(approved.headers["location"]).query)["code"][0]

            token = await client.post("/oauth/token", data={
                "grant_type": "authorization_code",
                "client_id": client_data["client_id"],
                "code": code,
                "redirect_uri": callback,
                "code_verifier": verifier,
            })
            assert token.status_code == 200, token.text
            assert token.json()["scope"] == requested_scope
            claims = app.state.hermes_mcp_auth.verified_claims(token.json()["access_token"])
            assert claims is not None
            assert claims["board"] == fixture.board
            assert claims["board_access"] == "write"


async def _test_oauth_http_read_choice_strips_create_and_is_global(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    app = create_app(_adapter(fixture), settings=settings, auth_service=AuthService(settings))
    verifier = "verifier-" + "c" * 35
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    callback = "https://chatgpt.com/connector/oauth/callback"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json={
                "client_name": "ChatGPT",
                "redirect_uris": [callback],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            })
            assert registration.status_code == 201, registration.text
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": "hermes:read hermes:create",
                "state": "state-read",
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
            assert approved.status_code == 303
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
    claims = app.state.hermes_mcp_auth.verified_claims(token.json()["access_token"])
    assert claims is not None
    assert "board" not in claims
    assert "board_access" not in claims


async def _test_beta_oauth_state_survives_fresh_service_and_isolated_from_stable(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path / "fixture")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))

    stable_settings = replace(_settings(), oauth_state_file=tmp_path / "stable-oauth-state.json")
    stable_client = AuthService(stable_settings).register_client(
        {
            "client_name": "Stable-only fixture client",
            "redirect_uris": ["https://chatgpt.com/connector/oauth/callback"],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "hermes:read",
        }
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
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")
    verifier = "beta-verifier-" + "d" * 32
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    callback = "https://chatgpt.com/connector/oauth/callback"
    scope = "hermes:read hermes:manage offline_access"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post(
                "/oauth/register",
                json={
                    "client_name": "Beta fixture client",
                    "redirect_uris": [callback],
                    "token_endpoint_auth_method": "none",
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "scope": scope,
                },
            )
            assert registration.status_code == 201
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": scope,
                "state": "beta-state",
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
            assert approved.status_code == 303
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
            assert token.status_code == 200
            initial = token.json()
            assert initial["scope"] == scope
            original_refresh = initial["refresh_token"]

    fresh_auth = AuthService(settings)
    assert fresh_auth.client(client_data["client_id"]).scope == scope
    with pytest.raises(OAuthError):
        fresh_auth.client(stable_client["client_id"])

    fresh_resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    fresh_app = create_app(
        board_resolver=fresh_resolver,
        settings=settings,
        auth_service=fresh_auth,
        surface="beta",
    )
    fresh_transport = httpx.ASGITransport(app=fresh_app)
    async with fresh_app.router.lifespan_context(fresh_app):
        async with httpx.AsyncClient(transport=fresh_transport, base_url=settings.public_base_url) as client:
            rotated_response = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_data["client_id"],
                    "refresh_token": original_refresh,
                },
            )
            assert rotated_response.status_code == 200
            rotated = rotated_response.json()
            assert rotated["refresh_token"] != original_refresh
            assert fresh_auth.verify_token(rotated["access_token"]) is not None
            assert rotated["scope"] == scope
            claims = fresh_auth.verified_claims(rotated["access_token"])
            assert claims is not None
            assert claims["scope"] == scope
            assert claims["board"] == fixture.board
            assert claims["board_access"] == "write"

            authorized_management = await client.post(
                "/mcp",
                headers={
                    "Authorization": f"Bearer {rotated['access_token']}",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-06-18",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "add_comment",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "task_id": "review-task",
                                "body": "refreshed grant management operation",
                            }
                        },
                    },
                },
            )
            assert authorized_management.status_code == 200
            management_result = authorized_management.json()["result"]
            assert management_result.get("isError") is not True
            assert management_result["structuredContent"]["board"] == fixture.board
            assert management_result["structuredContent"]["author"] == "chatgpt_mcp"

            reused_response = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_data["client_id"],
                    "refresh_token": original_refresh,
                },
            )
            assert reused_response.status_code == 400
            assert reused_response.json()["error"] == "invalid_grant"

    assert settings.oauth_state_file != stable_settings.oauth_state_file
    assert settings.oauth_state_file.is_file()
    assert stable_settings.oauth_state_file.is_file()


async def _test_oauth_http_pkce_flow_and_refresh_rotation(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    settings = _settings()
    app = create_app(_adapter(fixture), settings=settings, auth_service=AuthService(settings))
    verifier = "verifier-" + "a" * 35
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    callback = "https://chatgpt.com/connector/oauth/callback"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json={
                "client_name": "ChatGPT",
                "redirect_uris": [callback],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "hermes:read",
            })
            assert registration.status_code == 201, registration.text
            client_data = registration.json()

            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": "hermes:read",
                "state": "state-1",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            authorize = await client.get("/oauth/authorize", params=params)
            assert authorize.status_code == 200
            assert "read-only" in authorize.text

            bad_login = await client.post("/oauth/authorize", data={**params, "username": "chatgpt", "password": "wrong"})
            assert bad_login.status_code == 401
            assert "correct horse" not in bad_login.text

            approved = await client.post("/oauth/authorize", data={**params, "username": "chatgpt", "password": "correct horse battery staple"})
            assert approved.status_code == 303
            redirect = urlsplit(approved.headers["location"])
            returned = parse_qs(redirect.query)
            assert returned["state"] == ["state-1"]

            token = await client.post("/oauth/token", data={
                "grant_type": "authorization_code",
                "client_id": client_data["client_id"],
                "code": returned["code"][0],
                "redirect_uri": callback,
                "code_verifier": verifier,
            })
            assert token.status_code == 200, token.text
            token_data = token.json()
            assert token_data["token_type"] == "Bearer"
            assert token_data["refresh_token"]

            refresh = await client.post("/oauth/token", data={
                "grant_type": "refresh_token",
                "client_id": client_data["client_id"],
                "refresh_token": token_data["refresh_token"],
            })
            assert refresh.status_code == 200
            assert refresh.json()["refresh_token"] != token_data["refresh_token"]
