from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx

from hermes_chatgpt_mcp.auth import AuthService, BearerTokenVerifier
from hermes_chatgpt_mcp.diagnostics import fingerprint, scope_summary
from hermes_chatgpt_mcp.server import create_app

from .fixtures import make_hermes_fixture
from .test_oauth_http import _adapter
from .test_auth import _pkce, _settings


def _registration_scope(scope: str) -> dict[str, object]:
    return {
        "client_name": "ChatGPT",
        "redirect_uris": ["https://chatgpt.com/connector/oauth/callback"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": scope,
    }


def test_scope_summary_and_fingerprints_are_bounded_and_non_secret():
    value = "hermes:create hermes:read unknown-value"

    assert scope_summary(value, AuthService.supported_scopes) == "hermes:read hermes:create <unsupported>"
    assert scope_summary("", AuthService.supported_scopes) == "<empty>"
    assert scope_summary("unknown-value", AuthService.supported_scopes) == "<unsupported>"
    assert len(fingerprint("some credential-like value")) == 12
    assert "some credential-like value" not in fingerprint("some credential-like value")


def test_oauth_diagnostics_are_disabled_by_default(caplog):
    caplog.set_level(logging.INFO, logger="hermes_chatgpt_mcp.oauth")
    service = AuthService(_settings())
    service.register_client(_registration_scope("hermes:read"))

    assert not [record for record in caplog.records if "hermes_oauth_diagnostic" in record.getMessage()]


def test_oauth_diagnostics_trace_scopes_without_raw_credentials(caplog):
    settings = replace(_settings(), oauth_diagnostics=True)
    caplog.set_level(logging.INFO, logger="hermes_chatgpt_mcp.oauth")
    service = AuthService(settings)
    verifier, challenge = _pkce()
    client = service.register_client(_registration_scope("hermes:read hermes:create offline_access"))
    redirect_uri = client["redirect_uris"][0]
    code = service.create_authorization_code(
        client_id=client["client_id"],
        redirect_uri=redirect_uri,
        scope="hermes:read hermes:create offline_access",
        code_challenge=challenge,
    )
    bundle = service.exchange_code_bundle(
        code=code,
        client_id=client["client_id"],
        redirect_uri=redirect_uri,
        code_verifier=verifier,
    )
    rotated = service.refresh_bundle(
        refresh_token=bundle["refresh_token"],
        client_id=client["client_id"],
    )
    access = asyncio.run(BearerTokenVerifier(service).verify_token(rotated["access_token"]))

    assert access is not None
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if "hermes_oauth_diagnostic" in record.getMessage()
    ]
    stages = {event["stage"] for event in events}
    assert {
        "dcr",
        "authorize.grant",
        "token.authorization_code",
        "token.refresh.issue",
        "token.refresh.exchange",
        "mcp.bearer",
    } <= stages
    assert any(event.get("granted_scopes") == "hermes:read hermes:create offline_access" for event in events)
    assert any(event.get("effective_scopes") == "hermes:read hermes:create offline_access" for event in events)

    log_text = caplog.text
    for secret in (code, verifier, challenge, bundle["access_token"], bundle["refresh_token"], rotated["access_token"], rotated["refresh_token"]):
        assert secret not in log_text
    assert client["client_id"] not in log_text


def test_http_oauth_diagnostics_trace_request_boundaries(tmp_path, caplog):
    asyncio.run(_test_http_oauth_diagnostics_trace_request_boundaries(tmp_path, caplog))


async def _test_http_oauth_diagnostics_trace_request_boundaries(tmp_path, caplog):
    fixture = make_hermes_fixture(tmp_path)
    settings = replace(_settings(), oauth_diagnostics=True)
    caplog.set_level(logging.INFO, logger="hermes_chatgpt_mcp.oauth")
    auth = AuthService(settings)
    app = create_app(_adapter(fixture), settings=settings, auth_service=auth)
    verifier, challenge = _pkce()
    callback = "https://chatgpt.com/connector/oauth/callback"
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url, follow_redirects=False) as client:
            registration = await client.post("/oauth/register", json=_registration_scope("hermes:read hermes:create offline_access"))
            assert registration.status_code == 201
            client_data = registration.json()
            params = {
                "response_type": "code",
                "client_id": client_data["client_id"],
                "redirect_uri": callback,
                "scope": "hermes:read hermes:create offline_access",
                "state": "state-1",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": settings.public_base_url,
            }
            assert (await client.get("/oauth/authorize", params=params)).status_code == 200
            approved = await client.post(
                "/oauth/authorize",
                data={**params, "username": "chatgpt", "password": "correct horse battery staple"},
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
            token_data = token.json()
            refresh = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_data["client_id"],
                    "refresh_token": token_data["refresh_token"],
                },
            )
            assert refresh.status_code == 200
            refreshed = refresh.json()

    accepted = await BearerTokenVerifier(auth).verify_token(refreshed["access_token"])
    assert accepted is not None
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if "hermes_oauth_diagnostic" in record.getMessage()
    ]
    stages = {event["stage"] for event in events}
    assert {
        "dcr.request",
        "dcr.response",
        "authorize.request",
        "authorize.consent",
        "authorize.response",
        "authorize.grant",
        "token.request",
        "token.response",
        "token.authorization_code",
        "token.refresh.issue",
        "token.refresh.exchange",
        "mcp.bearer",
    } <= stages
    assert any(event.get("requested_scopes") == "hermes:read hermes:create offline_access" for event in events)
    assert any(event.get("effective_scopes") == "hermes:read hermes:create offline_access" for event in events)
    for secret in (code, verifier, challenge, token_data["access_token"], token_data["refresh_token"], refreshed["access_token"], refreshed["refresh_token"]):
        assert secret not in caplog.text
