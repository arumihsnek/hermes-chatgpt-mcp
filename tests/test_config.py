from __future__ import annotations

import pytest

from hermes_chatgpt_mcp.config import ConfigurationError, Settings


def test_settings_require_authentication(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    for name in ("MCP_OAUTH_USERNAME", "MCP_OAUTH_PASSWORD", "MCP_OAUTH_SIGNING_KEY"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigurationError, match="required"):
        Settings.from_env()


def test_settings_parse_bounded_values(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_PUBLIC_BASE_URL", "https://mcp.example.test")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("MCP_MAX_PAGE_SIZE", "25")
    monkeypatch.setenv("MCP_PORT", "9876")

    settings = Settings.from_env()

    assert settings.public_base_url == "https://mcp.example.test"
    assert settings.max_page_size == 25
    assert settings.port == 9876
    assert str(settings.oauth_state_file) == "/var/lib/hermes-chatgpt-mcp/oauth-state.json"


def test_settings_reject_oversized_page_limit(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("MCP_MAX_PAGE_SIZE", "501")

    with pytest.raises(ConfigurationError, match="MCP_MAX_PAGE_SIZE"):
        Settings.from_env()
