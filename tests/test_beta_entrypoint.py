from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


def test_beta_main_constructs_the_beta_policy_app_and_uses_configured_listener(monkeypatch):
    from hermes_chatgpt_mcp import beta_server

    settings = SimpleNamespace(surface="beta", host="127.0.0.1", port=8791)
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
