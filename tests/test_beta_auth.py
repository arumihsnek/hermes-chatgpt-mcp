from __future__ import annotations

from dataclasses import replace

import pytest

from hermes_chatgpt_mcp.auth import AuthService, BETA_AUTH_POLICY, OAuthError
from tests.test_auth import _settings


def _service() -> AuthService:
    return AuthService(replace(_settings(), surface="beta"), policy=BETA_AUTH_POLICY)


def test_beta_settings_select_beta_policy_without_explicit_injection():
    service = AuthService(replace(_settings(), surface="beta"))

    assert service.supported_scopes == BETA_AUTH_POLICY.supported_scopes


def test_beta_registration_accepts_management_and_board_administration_scopes():
    client = _service().register_client(
        {
            "redirect_uris": ["http://localhost/callback"],
            "token_endpoint_auth_method": "none",
            "scope": "hermes:read hermes:manage hermes:board:create",
        }
    )

    assert client["scope"] == "hermes:read hermes:manage hermes:board:create"


def test_beta_registration_default_does_not_grant_board_administration():
    client = _service().register_client(
        {
            "redirect_uris": ["http://localhost/callback"],
            "token_endpoint_auth_method": "none",
        }
    )

    assert client["scope"] == "hermes:read hermes:create"
    assert "hermes:board:create" not in client["scope"].split()
    assert "hermes:admin" not in client["scope"].split()


def test_beta_admin_scope_is_supported_but_requires_explicit_consent():
    service = _service()
    assert "hermes:admin" in service.supported_scopes
    token = service.issue_access_token(
        client_id="administrator",
        subject="user",
        scopes=["hermes:read", "hermes:admin"],
    )
    verified = service.verify_token(token)
    assert verified is not None
    assert "hermes:admin" in verified.scopes


def test_beta_management_scope_requires_one_write_board_grant():
    service = _service()

    with pytest.raises(OAuthError, match="selected board"):
        service.issue_access_token(
            client_id="manager",
            subject="user",
            scopes=["hermes:read", "hermes:manage"],
        )

    token = service.issue_access_token(
        client_id="manager",
        subject="user",
        scopes=["hermes:read", "hermes:manage"],
        board="board-a",
        board_access="write",
    )
    assert service.verified_claims(token)["board"] == "board-a"  # type: ignore[index]


def test_beta_board_administration_scope_never_carries_a_board_claim():
    service = _service()
    token = service.issue_access_token(
        client_id="administrator",
        subject="user",
        scopes=["hermes:read", "hermes:board:create"],
    )
    assert "board" not in service.verified_claims(token)  # type: ignore[operator]

    with pytest.raises(OAuthError, match="board grant"):
        service.issue_access_token(
            client_id="administrator",
            subject="user",
            scopes=["hermes:read", "hermes:board:create"],
            board="board-a",
            board_access="write",
        )


def test_admin_scope_combines_with_command_scopes_on_selected_board():
    service = _service()
    admin = service.issue_access_token(
        client_id="admin-global",
        subject="user",
        scopes=["hermes:read", "hermes:create", "hermes:manage", "hermes:board:create", "hermes:admin"],
        board="board-a",
        board_access="write",
    )
    claims = service.verified_claims(admin)
    assert claims is not None
    assert claims["board"] == "board-a"
    verified = service.verify_token(admin)
    assert verified is not None
    assert verified.scopes == [
        "hermes:read", "hermes:create", "hermes:manage", "hermes:board:create", "hermes:admin",
    ]
    # Admin-only grants remain global; command scopes require a selected board.
    with pytest.raises(OAuthError, match="selected board"):
        service.issue_access_token(
            client_id="admin-bad",
            subject="user",
            scopes=["hermes:read", "hermes:create", "hermes:board:create", "hermes:admin"],
        )


def test_beta_authorization_form_describes_separate_capabilities_without_legacy_labels():
    service = _service()
    html = service.authorization_form(
        query={"scope": "hermes:read hermes:create"},
        board_options=[{"slug": "board-a", "name": "Board A"}],
    )

    assert "Global read access" in html
    assert "task/card writes on the selected board" in html
    assert "Create boards globally" in html
    assert "Elevated administration, runtime, filesystem, and destructive actions" in html
    assert "offline_access" in html
    assert "scope_extra_board_create" in html
    assert "scope_extra_admin" in html
    assert "scope_extra_admin' value='hermes:board:create'" not in html
    assert "legacy" not in html.lower()


def test_stable_authorization_form_keeps_legacy_scope_controls_unchanged():
    service = AuthService(_settings())
    html = service.authorization_form(query={"scope": "hermes:read hermes:create"})

    assert "read-only access to all boards." in html
    assert "scope_extra_manage" not in html
    assert "scope_extra_admin" not in html


def test_beta_board_create_does_not_grant_admin_scope():
    service = _service()
    token = service.issue_access_token(
        client_id="board-creator",
        subject="user",
        scopes=["hermes:read", "hermes:board:create"],
    )

    verified = service.verify_token(token)
    assert verified is not None
    assert service.admin_scope not in verified.scopes
