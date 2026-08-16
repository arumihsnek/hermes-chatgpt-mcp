from __future__ import annotations

import base64
import hashlib
from dataclasses import replace

import pytest

from hermes_chatgpt_mcp.auth import AuthService, OAuthError
from hermes_chatgpt_mcp.config import Settings


def _settings() -> Settings:
    from pathlib import Path

    return Settings(
        hermes_agent_root=Path("/home/ubuntu/hermes-agent"),
        hermes_kanban_home=Path("/home/ubuntu/.hermes"),
        default_board="codex_app_server",
        public_base_url="https://mcp.example.test",
        host="127.0.0.1",
        port=8789,
        oauth_username="chatgpt",
        oauth_password="correct horse battery staple",
        oauth_signing_key="k" * 48,
    )


def _pkce():
    verifier = "verifier-" + "a" * 35
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def test_public_client_pkce_flow_issues_and_verifies_scoped_token():
    service = AuthService(_settings())
    client = service.register_client(
        {
            "client_name": "ChatGPT",
            "redirect_uris": ["https://chatgpt.com/connector/oauth/callback"],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "hermes:read",
        }
    )
    verifier, challenge = _pkce()
    code = service.create_authorization_code(
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        scope="hermes:read",
        code_challenge=challenge,
    )
    token = service.exchange_code(
        code=code,
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        code_verifier=verifier,
    )

    access = service.verify_token(token)
    assert access is not None
    assert access.client_id == client["client_id"]
    assert access.scopes == ["hermes:read"]
    assert service.verify_token(token + "tampered") is None


def test_public_client_registration_rejects_secret_auth_and_insecure_redirect():
    service = AuthService(_settings())

    with pytest.raises(OAuthError):
        service.register_client(
            {
                "client_name": "bad",
                "redirect_uris": ["https://chatgpt.com/callback"],
                "token_endpoint_auth_method": "client_secret_basic",
            }
        )
    with pytest.raises(OAuthError):
        service.register_client(
            {
                "client_name": "bad",
                "redirect_uris": ["http://evil.example/callback"],
                "token_endpoint_auth_method": "none",
            }
        )


def test_authorization_code_is_single_use_and_pkce_is_required():
    service = AuthService(_settings())
    client = service.register_client(
        {
            "client_name": "ChatGPT",
            "redirect_uris": ["http://localhost/callback"],
            "token_endpoint_auth_method": "none",
        }
    )
    verifier, challenge = _pkce()
    code = service.create_authorization_code(
        client_id=client["client_id"],
        redirect_uri="http://localhost/callback",
        scope="hermes:read",
        code_challenge=challenge,
    )
    with pytest.raises(OAuthError):
        service.exchange_code(
            code=code,
            client_id=client["client_id"],
            redirect_uri="http://localhost/callback",
            code_verifier="wrong",
        )
    token = service.exchange_code(
        code=code,
        client_id=client["client_id"],
        redirect_uri="http://localhost/callback",
        code_verifier=verifier,
    )
    assert service.verify_token(token) is not None
    with pytest.raises(OAuthError):
        service.exchange_code(
            code=code,
            client_id=client["client_id"],
            redirect_uri="http://localhost/callback",
            code_verifier=verifier,
        )


def test_create_scope_is_separate_and_creation_grant_also_contains_read():
    service = AuthService(_settings())
    with pytest.raises(OAuthError, match="requires hermes:read"):
        service.register_client(
            {
                "redirect_uris": ["http://localhost/callback"],
                "token_endpoint_auth_method": "none",
                "scope": "hermes:create",
            }
        )

    read_token = service.issue_access_token(client_id="read-only", subject="user")
    create_token = service.issue_access_token(
        client_id="creator",
        subject="user",
        scopes=["hermes:read", "hermes:create"],
    )
    assert service.verify_token(read_token).scopes == ["hermes:read"]
    assert service.verify_token(create_token).scopes == ["hermes:read", "hermes:create"]


def test_dcr_clients_and_refresh_rotation_survive_auth_service_restart(tmp_path):
    state_file = tmp_path / "oauth" / "state.json"
    settings = replace(_settings(), oauth_state_file=state_file)
    first = AuthService(settings)
    client = first.register_client(
        {
            "client_name": "ChatGPT",
            "redirect_uris": ["https://chatgpt.com/connector/oauth/callback"],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "hermes:read hermes:create offline_access",
        }
    )
    verifier, challenge = _pkce()
    code = first.create_authorization_code(
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        scope="hermes:read hermes:create offline_access",
        code_challenge=challenge,
    )
    bundle = first.exchange_code_bundle(
        code=code,
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        code_verifier=verifier,
    )
    assert state_file.stat().st_mode & 0o077 == 0
    assert bundle["refresh_token"] not in state_file.read_text(encoding="utf-8")

    second = AuthService(settings)
    assert second.client(client["client_id"]).client_id == client["client_id"]
    rotated = second.refresh_bundle(
        refresh_token=bundle["refresh_token"],
        client_id=client["client_id"],
    )
    assert rotated["scope"] == "hermes:read hermes:create offline_access"
    with pytest.raises(OAuthError, match="invalid refresh token"):
        second.refresh_bundle(
            refresh_token=bundle["refresh_token"],
            client_id=client["client_id"],
        )
