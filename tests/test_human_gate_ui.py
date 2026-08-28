import re

from hermes_chatgpt_mcp.human_gate_ui import (
    HUMAN_GATE_READBACK_TOOL,
    build_human_gate_ui_html,
    deep_link,
    render_readback,
)


def test_human_gate_ui_is_non_authoritative():
    html = build_human_gate_ui_html()
    assert 'data-ui-version="v1"' in html
    assert "awaiting human authority" in html.lower()
    assert "dashboard" in html.lower()
    assert "YES" not in html and "NO" not in html
    assert "/comments" not in html
    assert "HERMES_HUMAN_BINDING_SECRET" not in html
    assert "canonical_session_id" not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_deep_link_contains_only_exact_task_target():
    value = deep_link("https://dashboard.example", "t_gate-1")
    assert value == "https://dashboard.example/tasks/t_gate-1#human-gate-t_gate-1"
    assert all(token not in value for token in ("nonce", "candidate", "author", "package"))


def test_readback_is_verbatim_and_redacted():
    data = render_readback({
        "gate_state": "authorized",
        "binding_fingerprint": "a1b2c3d4",
        "consumed_at": "2026-08-27T20:00:00Z",
        "consumed_by_principal": "user",
        "window": {"window_start": "2026-08-27T19:00:00Z", "window_end": "2026-08-27T21:00:00Z"},
    })
    assert data["gate_state"] == "authorized"
    assert data["binding_fingerprint"] == "a1b2c3d4"
    assert data["consumed_by_principal"] == "user"
    assert set(data) == {"gate_state", "binding_fingerprint", "consumed_at", "consumed_by_principal", "window"}


def test_readback_rejects_untrusted_fields_and_invalid_state():
    data = render_readback({"gate_state": "authorized", "signature": "secret", "nonce": "bad"})
    assert data["gate_state"] == "authorized"
    assert "signature" not in data and "nonce" not in data
    assert HUMAN_GATE_READBACK_TOOL == "get_human_gate_readback"
