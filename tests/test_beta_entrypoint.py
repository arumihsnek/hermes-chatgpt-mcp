from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


def test_beta_main_constructs_the_beta_policy_app_and_uses_configured_listener(monkeypatch):
    from hermes_chatgpt_mcp import beta_server

    monkeypatch.setenv("MCP_ENV_FILE", beta_server.BETA_ENV_FILE)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    settings = SimpleNamespace(
        surface="beta",
        host="127.0.0.1",
        port=8791,
        public_base_url="https://kanban-beta.hermesinthenight.duckdns.org",
        oauth_state_file=Path("/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json"),
        oauth_signing_key="b" * 48,
    )
    calls: dict[str, object] = {}
    app = object()
    auth = object()

    monkeypatch.setattr(beta_server, "Settings", SimpleNamespace(from_env=lambda: settings))

    def make_auth(received_settings, *, policy):
        calls["auth"] = (received_settings, policy)
        return auth

    def make_app(*, settings, surface, auth_service):
        calls["app"] = (settings, surface, auth_service)
        return app

    def run(received_app, *, host, port, log_level, access_log):
        calls["uvicorn"] = (received_app, host, port, log_level, access_log)

    monkeypatch.setattr(beta_server, "AuthService", make_auth)
    monkeypatch.setattr(beta_server, "create_app", make_app)
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=run))
    monkeypatch.setenv("MCP_LOG_LEVEL", "WARNING")

    beta_server.main()

    assert calls["auth"] == (settings, beta_server.BETA_AUTH_POLICY)
    assert calls["app"] == (settings, "beta", auth)
    assert calls["uvicorn"] == (app, "127.0.0.1", 8791, "warning", False)


def test_beta_main_rejects_a_non_beta_configuration_before_constructing_services(monkeypatch):
    from hermes_chatgpt_mcp import beta_server

    settings = SimpleNamespace(surface="stable")
    monkeypatch.setattr(beta_server, "Settings", SimpleNamespace(from_env=lambda: settings))

    with pytest.raises(AssertionError, match="MCP_SURFACE=beta"):
        beta_server.main()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("public_base_url", "https://kanban.hermesinthenight.duckdns.org", "public origin"),
        ("oauth_state_file", Path("/var/lib/hermes-chatgpt-mcp/oauth-state.json"), "state"),
    ],
)
def test_beta_main_rejects_stable_origin_or_oauth_state_before_service_construction(
    monkeypatch, field, value, message
):
    from hermes_chatgpt_mcp import beta_server

    monkeypatch.setenv("MCP_ENV_FILE", beta_server.BETA_ENV_FILE)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    settings = SimpleNamespace(
        surface="beta",
        host="127.0.0.1",
        port=8791,
        public_base_url="https://kanban-beta.hermesinthenight.duckdns.org",
        oauth_state_file=Path("/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json"),
        oauth_signing_key="b" * 48,
    )
    setattr(settings, field, value)
    monkeypatch.setattr(beta_server, "Settings", SimpleNamespace(from_env=lambda: settings))
    monkeypatch.setattr(
        beta_server,
        "AuthService",
        lambda *_args, **_kwargs: pytest.fail("beta isolation must fail before AuthService construction"),
    )

    with pytest.raises((AssertionError, RuntimeError), match=message):
        beta_server.main()
