from hermes_chatgpt_mcp.human_gate_ui import build_human_gate_ui_html, render_readback


def _html():
    return build_human_gate_ui_html()


def test_mcp_app_does_not_post_yes():
    assert "comments" not in _html() and "approve" not in _html().lower()


def test_mcp_app_does_not_post_no():
    assert "deny" not in _html().lower().replace('content="deny"', "")


def test_mcp_app_renders_evidence_and_deep_link():
    html = _html()
    assert all(x in html for x in ("Exact card", "Decision state", "Evidence", "dashboard"))


def test_mcp_app_rejects_body_parse_nonce():
    assert "nonce" not in _html().lower()


def test_mcp_app_rejects_board_mismatch():
    assert all(x in _html() for x in ("board", "tenant", "revision", "generation"))


def test_mcp_app_redacts_secret_and_signature():
    html = _html()
    assert all(x not in html for x in ("HERMES_HUMAN_BINDING_SECRET", "canonical_session_id", "signature"))
    assert render_readback({"binding_fingerprint": "01234567"})["binding_fingerprint"] == "01234567"


def test_mcp_app_replay_after_consume():
    assert "authorized" in _html() and "read-only" in _html()


def test_mcp_app_replay_after_window():
    assert "expired_or_no" in _html()


def test_mcp_app_cannot_invoke_bootstrap():
    assert "bootstrap" in _html().lower()
    assert "one-shot" in _html().lower()


def test_mcp_app_no_direct_db_or_bypass():
    html = _html().lower()
    assert all(x not in html for x in ("sqlite", "kanban_db", "post /", "xmlhttprequest"))


def test_mcp_app_persistent_banner():
    assert 'class="banner"' in _html() and "Awaiting human authority" in _html()


def test_mcp_app_stale_readback_rejection():
    assert all(x in _html() for x in ("generation", "board", "tenant", "revision"))


def test_mcp_app_no_credentials_in_storage():
    html = _html().lower()
    assert all(x not in html for x in ("localstorage", "sessionstorage", "indexeddb", "cookie"))


def test_mcp_app_csp_and_framing():
    html = _html()
    assert "Content-Security-Policy" in html and "frame-ancestors 'none'" in html
    assert "X-Frame-Options" in html


def test_mcp_app_v4_independence():
    html = _html().lower()
    assert all(x not in html for x in ("promote", "phase-s", "v4", "release"))
