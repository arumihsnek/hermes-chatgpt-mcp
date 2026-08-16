from __future__ import annotations

from pathlib import Path


def test_systemd_unit_keeps_query_command_and_oauth_state_boundaries():
    unit = Path("deploy/systemd/hermes-chatgpt-mcp.service").read_text(encoding="utf-8")
    assert "ProtectSystem=full" in unit
    assert "ProtectHome=read-only" in unit
    assert "NoNewPrivileges=yes" in unit
    assert "StateDirectory=hermes-chatgpt-mcp" in unit
    assert "StateDirectoryMode=0700" in unit
    assert "/var/lib/hermes-chatgpt-mcp" in unit
    assert "/home/ubuntu/.hermes/kanban/boards/codex_app_server" in unit
    assert "ReadWritePaths=/home/ubuntu/.hermes\n" not in unit


def test_oci_installer_preserves_private_oauth_state_configuration():
    installer = Path("scripts/install_oci.sh").read_text(encoding="utf-8")
    assert '"MCP_OAUTH_STATE_FILE": "/var/lib/hermes-chatgpt-mcp/oauth-state.json"' in installer
    assert 'path.chmod(0o600)' in installer
    assert "systemctl restart" in installer
