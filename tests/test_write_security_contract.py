from __future__ import annotations

import pytest

from hermes_chatgpt_mcp.ui_write_contract import (
    REQUIRED_SCOPE_CLAIM,
    UI_RESOURCE_URI_V2,
    UiCapabilityIssuer,
    check_create_fields,
    check_operation_allowed,
    sanitize_ui_payload,
)


FIXED_NOW = 1_700_000_000.0


def _issuer() -> UiCapabilityIssuer:
    return UiCapabilityIssuer(clock=lambda: FIXED_NOW)


def test_issued_capability_emits_exact_required_scope_claim():
    capability = _issuer().issue(subject="session-1", board="alpha", tenant="tenant-1")
    claims = capability.to_dict()

    assert claims["scope"] == REQUIRED_SCOPE_CLAIM
    assert claims["scope"] == "hermes:read hermes:create"
    assert claims["operations"] == ["create_task"]
    assert claims["resource_uri"] == UI_RESOURCE_URI_V2


def test_capability_scope_is_validated_fail_closed():
    issuer = _issuer()
    capability = issuer.issue(subject="session-1", board="alpha", tenant="tenant-1")

    assert issuer.validate(capability) == (True, None)
    assert issuer.validate(
        {**capability.to_dict(), "scope": "hermes:read"}
    ) == (False, "SCOPE_MISSING_OR_INVALID")
    assert issuer.validate(
        {**capability.to_dict(), "scope": "hermes:read hermes:create hermes:manage"}
    ) == (False, "SCOPE_MISSING_OR_INVALID")
    assert issuer.validate(
        {key: value for key, value in capability.to_dict().items() if key != "scope"}
    ) == (False, "MALFORMED_CAPABILITY")


def test_issuer_rejects_unsupported_scope_or_operation_instead_of_downgrading():
    issuer = _issuer()
    with pytest.raises(ValueError, match="scope"):
        issuer.issue(
            subject="session-1",
            board="alpha",
            tenant="tenant-1",
            scope="hermes:read",
        )
    with pytest.raises(ValueError, match="operation"):
        issuer.issue(
            subject="session-1",
            board="alpha",
            tenant="tenant-1",
            operations=("request_review",),
        )


def test_capability_context_mismatch_is_fail_closed():
    issuer = _issuer()
    capability = issuer.issue(subject="session-1", board="alpha", tenant="tenant-1")

    assert issuer.validate(capability, expected_subject="other") == (False, "CONTEXT_MISMATCH")
    assert issuer.validate(capability, expected_board="other") == (False, "CONTEXT_MISMATCH")
    assert issuer.validate(capability, expected_tenant="other") == (False, "CONTEXT_MISMATCH")
    assert issuer.validate(capability, expected_capability_id="other") == (False, "CONTEXT_MISMATCH")


def test_value_level_sanitization_redacts_bearer_and_authorization_under_benign_keys():
    payload = {
        "note": "Authorization: Bearer abc123456789",
        "nested": ["bearer secret-token-value-123456", {"description": "Bearer xyz987654321"}],
    }

    sanitized = sanitize_ui_payload(payload)

    assert "abc123456789" not in sanitized["note"]
    assert "secret-token-value-123456" not in sanitized["nested"][0]
    assert "xyz987654321" not in sanitized["nested"][1]["description"]
    assert "[REDACTED]" in sanitized["note"]


def test_value_level_sanitization_redacts_internal_paths_and_dsns_under_benign_keys():
    payload = {
        "description": "The path is /home/user/secret.txt",
        "details": {
            "trace": "/private/workspace/run.log and /tmp/cache",
            "config": "postgres://user:pass@host/db",
        },
    }

    sanitized = sanitize_ui_payload(payload)

    assert "/home/" not in sanitized["description"]
    assert "/private/" not in sanitized["details"]["trace"]
    assert "/tmp/" not in sanitized["details"]["trace"]
    assert "postgres://" not in sanitized["details"]["config"]
    assert "[INTERNAL_PATH]/user/secret.txt" in sanitized["description"]
    assert "[REDACTED]://" in sanitized["details"]["config"]


def test_sanitization_does_not_over_redact_ordinary_card_text():
    payload = {
        "title": "Token secret internal",
        "body": "This card discusses a secret token in ordinary language.",
        "comment": "The internal review is complete.",
    }

    assert sanitize_ui_payload(payload) == payload


def test_sensitive_key_names_remain_defense_in_depth():
    payload = {"password": "ordinary-value", "api_key": "ordinary-value"}

    assert sanitize_ui_payload(payload) == {
        "password": "[REDACTED]",
        "api_key": "[REDACTED]",
    }


def test_ui_operation_and_field_allowlist_fail_closed():
    assert check_operation_allowed("create_task") == (True, None)
    assert check_operation_allowed("request_review") == (False, "GATE_FORBIDDEN_FROM_UI")
    assert check_operation_allowed("unknown-operation") == (False, "UI_OPERATION_FORBIDDEN")
    assert check_create_fields({"title", "body", "idempotency_key"}) == (True, None)
    assert check_create_fields({"title", "tenant"}) == (False, "UI_FIELD_FORBIDDEN")
