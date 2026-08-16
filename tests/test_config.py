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
    monkeypatch.setenv("MCP_KANBAN_READ_BOARDS", "board-a,board-b")
    monkeypatch.setenv("MCP_KANBAN_CREATE_BOARDS", "board-a")
    monkeypatch.setenv("MCP_MAX_BOARD_COUNT", "12")
    monkeypatch.setenv("MCP_OAUTH_DIAGNOSTICS", "true")

    settings = Settings.from_env()

    assert settings.public_base_url == "https://mcp.example.test"
    assert settings.max_page_size == 25
    assert settings.port == 9876
    assert settings.kanban_read_boards == ("board-a", "board-b")
    assert settings.kanban_create_boards == ("board-a",)
    assert settings.max_board_count == 12
    assert settings.oauth_diagnostics is True
    assert str(settings.oauth_state_file) == "/var/lib/hermes-chatgpt-mcp/oauth-state.json"
    assert settings.surface == "stable"
    assert settings.board_create_enabled is False


def test_settings_parse_beta_surface_and_board_create_flag(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("MCP_SURFACE", "beta")
    monkeypatch.setenv("MCP_BOARD_CREATE_ENABLED", "true")

    settings = Settings.from_env()

    assert settings.surface == "beta"
    assert settings.board_create_enabled is True


def test_settings_reject_oversized_page_limit(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("MCP_MAX_PAGE_SIZE", "501")

    with pytest.raises(ConfigurationError, match="MCP_MAX_PAGE_SIZE"):
        Settings.from_env()


def test_settings_reject_invalid_oauth_diagnostics_flag(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("MCP_OAUTH_DIAGNOSTICS", "maybe")

    with pytest.raises(ConfigurationError, match="MCP_OAUTH_DIAGNOSTICS"):
        Settings.from_env()
