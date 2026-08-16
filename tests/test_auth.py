from __future__ import annotations

import base64
import hashlib
import json
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
        board="board-a",
        board_access="write",
    )
    assert service.verify_token(read_token).scopes == ["hermes:read"]
    assert service.verify_token(create_token).scopes == ["hermes:read", "hermes:create"]


@pytest.mark.parametrize("scope", ["hermes:manage", "hermes:board:create"])
def test_unsupported_scope_is_rejected(scope):
    service = AuthService(_settings())

    with pytest.raises(OAuthError, match="unsupported scope"):
        service.register_client(
            {
                "redirect_uris": ["http://localhost/callback"],
                "token_endpoint_auth_method": "none",
                "scope": f"hermes:read {scope}",
            }
        )


def test_authorization_can_request_supported_scope_beyond_dcr_default():
    service = AuthService(_settings())
    client = service.register_client(
        {
            "client_name": "ChatGPT",
            "redirect_uris": ["https://chatgpt.com/connector/oauth/callback"],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
        }
    )
    verifier, challenge = _pkce()
    scope = "hermes:read hermes:create offline_access"

    code = service.create_authorization_code(
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        scope=scope,
        code_challenge=challenge,
        board="board-a",
        write_grant=True,
    )
    token = service.exchange_code(
        code=code,
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        code_verifier=verifier,
    )

    assert service.verify_token(token).scopes == scope.split()


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
        board="board-a",
        write_grant=True,
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
    rotated_claims = second.verified_claims(rotated["access_token"])
    assert rotated_claims is not None
    assert rotated_claims["board"] == "board-a"
    assert rotated_claims["board_access"] == "write"
    with pytest.raises(OAuthError, match="invalid refresh token"):
        second.refresh_bundle(
            refresh_token=bundle["refresh_token"],
            client_id=client["client_id"],
        )


def test_legacy_unbound_write_refresh_is_dropped_without_blocking_restart(tmp_path):
    state_file = tmp_path / "oauth" / "state.json"
    state_file.parent.mkdir(mode=0o700)
    legacy_read = "legacy-read-refresh"
    legacy_write = "legacy-unbound-write-refresh"
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "clients": {
                    "legacy-client": {
                        "client_id": "legacy-client",
                        "redirect_uris": ["https://chatgpt.com/connector/oauth/callback"],
                        "grant_types": ["authorization_code", "refresh_token"],
                        "scope": "hermes:read",
                        "client_name": "ChatGPT",
                        "issued_at": 1,
                    }
                },
                "refresh_tokens": {
                    hashlib.sha256(legacy_read.encode()).hexdigest(): {
                        "client_id": "legacy-client",
                        "subject": "ChatGPT",
                        "scope": "hermes:read",
                        "expires_at": 4_000_000_000,
                    },
                    hashlib.sha256(legacy_write.encode()).hexdigest(): {
                        "client_id": "legacy-client",
                        "subject": "ChatGPT",
                        "scope": "hermes:read hermes:create offline_access",
                        "expires_at": 4_000_000_000,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state_file.chmod(0o600)
    service = AuthService(replace(_settings(), oauth_state_file=state_file))

    rotated = service.refresh_bundle(refresh_token=legacy_read, client_id="legacy-client")
    assert rotated["scope"] == "hermes:read"
    with pytest.raises(OAuthError, match="invalid refresh token"):
        service.refresh_bundle(refresh_token=legacy_write, client_id="legacy-client")
    assert json.loads(state_file.read_text(encoding="utf-8"))["version"] == 2


def test_write_grant_is_bound_to_one_board_and_revocable(tmp_path):
    state_file = tmp_path / "oauth" / "state.json"
    settings = replace(_settings(), oauth_state_file=state_file)
    service = AuthService(settings)
    client = service.register_client(
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
    code = service.create_authorization_code(
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        scope="hermes:read hermes:create offline_access",
        code_challenge=challenge,
        board="board-a",
        write_grant=True,
    )

    bundle = service.exchange_code_bundle(
        code=code,
        client_id=client["client_id"],
        redirect_uri=client["redirect_uris"][0],
        code_verifier=verifier,
    )
    access = service.verify_token(bundle["access_token"])
    assert access is not None
    claims = service.verified_claims(bundle["access_token"])
    assert claims is not None
    assert claims["board"] == "board-a"
    assert claims["board_access"] == "write"

    rotated = service.refresh_bundle(
        refresh_token=bundle["refresh_token"],
        client_id=client["client_id"],
    )
    rotated_access = service.verify_token(rotated["access_token"])
    assert rotated_access is not None
    rotated_claims = service.verified_claims(rotated["access_token"])
    assert rotated_claims is not None
    assert rotated_claims["board"] == "board-a"
    assert rotated_claims["board_access"] == "write"

    service.revoke_token(rotated["refresh_token"], client_id=client["client_id"])
    assert service.verify_token(rotated["access_token"]) is None
    with pytest.raises(OAuthError, match="invalid refresh token"):
        service.refresh_bundle(
            refresh_token=rotated["refresh_token"],
            client_id=client["client_id"],
        )
