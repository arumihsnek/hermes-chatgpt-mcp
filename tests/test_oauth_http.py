from __future__ import annotations

import asyncio
import base64
import hashlib
from urllib.parse import parse_qs, urlsplit

import httpx

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.auth import AuthService
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


def test_oauth_http_pkce_flow_and_refresh_rotation(tmp_path):
    asyncio.run(_test_oauth_http_pkce_flow_and_refresh_rotation(tmp_path))


def test_oauth_http_dcr_default_then_create_authorization(tmp_path):
    asyncio.run(_test_oauth_http_dcr_default_then_create_authorization(tmp_path))


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
            assert client_data["scope"] == "hermes:read"

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

            approved = await client.post(
                "/oauth/authorize",
                data={**params, "username": "chatgpt", "password": "correct horse battery staple"},
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
