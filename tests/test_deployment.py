from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.oci_beta_edge import EdgeConfigError, render_edge_config


BETA_HOSTNAME = "kanban-beta.hermesinthenight.duckdns.org"
BETA_INCLUDE = "/usr/local/openresty/nginx/conf/conf.d/hermes-chatgpt-mcp-beta.locations"
BEGIN = "# BEGIN hermes-chatgpt-mcp-beta managed include"
END = "# END hermes-chatgpt-mcp-beta managed include"


def _beta_edge(*, managed_block: str = "", prefix: str = "", listen: str = "listen 443 ssl;\n") -> str:
    return (
        "events {}\n"
        "http {\n"
        f"{prefix}"
        "    server {\n"
        f"        {listen}"
        f"        server_name {BETA_HOSTNAME};\n"
        f"{managed_block}"
        "    }\n"
        "}\n"
    )


def _managed_block(include: str = BETA_INCLUDE) -> str:
    return f"        {BEGIN}\n        include {include};\n        {END}\n"


def test_systemd_unit_keeps_query_command_and_oauth_state_boundaries():
    unit = Path("deploy/systemd/hermes-chatgpt-mcp.service").read_text(encoding="utf-8")
    assert "ProtectSystem=full" in unit
    assert "ProtectHome=read-only" in unit
    assert "NoNewPrivileges=yes" in unit
    assert "StateDirectory=hermes-chatgpt-mcp" in unit
    assert "StateDirectoryMode=0700" in unit
    assert "Environment=MCP_OAUTH_DIAGNOSTICS=0" in unit
    assert "/var/lib/hermes-chatgpt-mcp" in unit
    assert "ReadWritePaths=/home/ubuntu/.hermes/kanban/boards /var/lib/hermes-chatgpt-mcp" in unit
    assert "/home/ubuntu/.hermes/kanban.db" not in unit
    assert "ReadWritePaths=/home/ubuntu/.hermes\n" not in unit


def test_oci_installer_preserves_private_oauth_state_configuration():
    installer = Path("scripts/install_oci.sh").read_text(encoding="utf-8")
    assert '"MCP_OAUTH_STATE_FILE": "/var/lib/hermes-chatgpt-mcp/oauth-state.json"' in installer
    assert 'path.chmod(0o600)' in installer
    assert "systemctl restart" in installer
    assert '"HERMES_KANBAN_BOARD": "codex_app_server"' not in installer
    assert '"MCP_KANBAN_READ_BOARDS": "codex_app_server,dashboard"' not in installer
    assert '"MCP_KANBAN_CREATE_BOARDS": "codex_app_server,dashboard"' not in installer


def test_beta_unit_has_a_separate_listener_state_and_narrow_sandbox():
    unit = Path("deploy/systemd/hermes-chatgpt-mcp-beta.service").read_text(encoding="utf-8")

    assert "Description=Hermes ChatGPT MCP beta service" in unit
    assert "User=ubuntu" in unit
    assert "WorkingDirectory=/home/ubuntu/code/hermes-chatgpt-mcp/.worktrees/hermes-chatgpt-mcp-beta" in unit
    assert "ExecStart=/home/ubuntu/hermes-agent/venv/bin/python -m hermes_chatgpt_mcp.beta_server" in unit
    assert "Environment=MCP_SURFACE=beta" in unit
    assert "Environment=MCP_ENV_FILE=/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env" in unit
    assert "Environment=MCP_PORT=8791" in unit
    assert "Environment=MCP_BOARD_CREATE_ENABLED=1" in unit
    assert "Environment=MCP_OAUTH_STATE_FILE=/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json" in unit
    assert "Restart=on-failure" in unit
    assert "StateDirectory=hermes-chatgpt-mcp-beta" in unit
    assert "ReadWritePaths=/home/ubuntu/.hermes/kanban/boards /var/lib/hermes-chatgpt-mcp-beta" in unit
    assert "/var/lib/hermes-chatgpt-mcp/oauth-state.json" not in unit
    assert "/home/ubuntu/.hermes/kanban.db" not in unit
    assert "ReadWritePaths=/home/ubuntu/.hermes\n" not in unit


def test_beta_openresty_include_is_limited_to_the_beta_mcp_routes():
    include = Path("deploy/openresty/kanban-mcp-beta.conf").read_text(encoding="utf-8")

    assert "kanban-beta.hermesinthenight.duckdns.org" in include
    assert "location = /mcp" in include
    assert "location = /healthz" in include
    assert "location = /.well-known/oauth-protected-resource" in include
    assert "location = /.well-known/oauth-authorization-server" in include
    assert "location ^~ /oauth/" in include
    assert include.count("proxy_pass http://127.0.0.1:8791;") == 6
    assert "kanban.hermesinthenight.duckdns.org" not in include
    # Root POSTs must reach the MCP transport (ChatGPT connectors use the
    # declared server URL / OAuth issuer as the session endpoint) while
    # GET/HEAD keep serving the landing page, plus discovery fallback for
    # connectors configured with a /mcp-suffixed URL. The named-location
    # rewrite is required because a literal URI in proxy_pass is invalid
    # inside named locations, and rewrite/set are invalid inside limit_except.
    assert "location = / {\n    error_page 405 = @beta_mcp_root;" in include
    assert "location @beta_mcp_root {" in include
    assert "rewrite ^ /mcp break;" in include
    assert "location ^~ /mcp/.well-known/ {" in include
    assert 'proxy_pass http://127.0.0.1:8791/.well-known/;' in include


def test_beta_installer_keeps_credentials_private_and_never_restarts_stable():
    installer = Path("scripts/install_oci_beta.sh").read_text(encoding="utf-8")
    unit = Path("deploy/systemd/hermes-chatgpt-mcp-beta.service").read_text(encoding="utf-8")
    unit_env_file = re.search(r"(?m)^EnvironmentFile=(\S+)$", unit)
    default_env_file = re.search(r'(?m)^default_env_file="([^"]+)"$', installer)

    assert "hermes-chatgpt-mcp-beta.service" in installer
    assert "kanban-mcp-beta.conf" in installer
    assert unit_env_file is not None
    assert default_env_file is not None
    assert default_env_file.group(1) == unit_env_file.group(1)
    assert '"MCP_SURFACE": "beta"' in installer
    assert '"MCP_PORT": "8791"' in installer
    assert '"MCP_BOARD_CREATE_ENABLED": "1"' in installer
    assert '"MCP_OAUTH_STATE_FILE": "/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json"' in installer
    assert 'values.setdefault("MCP_OAUTH_SIGNING_KEY"' in installer
    assert 'path.chmod(0o600)' in installer
    assert 'git -C "$candidate_worktree" worktree list --porcelain' in installer
    assert '"$requested_commit" != "$candidate_commit"' in installer
    assert "openresty -t" in installer
    assert "systemctl restart \"$service_name\"" in installer
    assert "hermes-chatgpt-mcp.service" not in installer


def test_beta_installer_targets_the_container_locations_filename():
    installer = Path("scripts/install_oci_beta.sh").read_text(encoding="utf-8")

    assert 'include_target="$include_dir/hermes-chatgpt-mcp-beta.locations"' in installer
    assert (
        'include_inside="/usr/local/openresty/nginx/conf/conf.d/'
        'hermes-chatgpt-mcp-beta.locations"'
    ) in installer
    assert 'include_target="$include_dir/hermes-chatgpt-mcp-beta.conf"' not in installer
    assert (
        'include_inside="/usr/local/openresty/nginx/conf/conf.d/'
        'hermes-chatgpt-mcp-beta.conf"'
    ) not in installer


@pytest.mark.parametrize(
    "edge",
    [
        _beta_edge(managed_block=f"        {BEGIN}\n"),
        _beta_edge(managed_block=f"        {END}\n"),
        _beta_edge(managed_block=_managed_block("/usr/local/openresty/nginx/conf/conf.d/wrong.conf")),
        _beta_edge(managed_block=_managed_block() + _managed_block()),
        _beta_edge(prefix=f"    {BEGIN}\n    include {BETA_INCLUDE};\n    {END}\n"),
    ],
)
def test_beta_edge_validation_fails_closed_for_malformed_or_misplaced_managed_blocks(edge):
    with pytest.raises(EdgeConfigError):
        render_edge_config(edge, include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME)


def test_beta_edge_render_is_idempotent_and_inserts_only_inside_beta_vhost():
    rendered = render_edge_config(_beta_edge(), include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME)
    assert rendered.count(BEGIN) == 1
    assert rendered.count(END) == 1
    server_start = rendered.index("server {")
    server_end = rendered.index("\n    }", server_start)
    assert server_start < rendered.index(BEGIN) < server_end
    assert render_edge_config(rendered, include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME) == rendered


def test_beta_edge_rejects_managed_markers_nested_inside_a_location():
    edge = _beta_edge(
        managed_block=(
            "        location /mcp {\n"
            f"{_managed_block()}"
            "        }\n"
        )
    )

    with pytest.raises(EdgeConfigError):
        render_edge_config(edge, include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME)


def test_beta_edge_rejects_a_beta_server_name_after_a_closed_stable_vhost():
    edge = (
        "events {}\n"
        "http {\n"
        "    server {\n"
        "        server_name stable.example.test;\n"
        "    }\n"
        f"    server_name {BETA_HOSTNAME};\n"
        "}\n"
    )

    with pytest.raises(EdgeConfigError):
        render_edge_config(edge, include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME)


def test_beta_edge_rejects_a_beta_server_name_nested_inside_a_location():
    edge = (
        "events {}\n"
        "http {\n"
        "    server {\n"
        "        location /mcp {\n"
        f"            server_name {BETA_HOSTNAME};\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    with pytest.raises(EdgeConfigError):
        render_edge_config(edge, include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME)


def test_beta_edge_rejects_quoted_multiline_server_name_text_without_injection():
    edge = (
        "events {}\n"
        "http {\n"
        "    server {\n"
        "        server_name stable.example.test;\n"
        "        set $quoted \"line one\n"
        f"server_name {BETA_HOSTNAME};\n"
        "line three\";\n"
        "    }\n"
        "}\n"
    )

    with pytest.raises(EdgeConfigError):
        render_edge_config(edge, include_path=BETA_INCLUDE, hostname=BETA_HOSTNAME)
    assert BEGIN not in edge


def test_beta_installer_validates_before_copying_and_rolls_back_all_new_artifacts():
    installer = Path("scripts/install_oci_beta.sh").read_text(encoding="utf-8")

    validate_at = installer.index('"$edge_helper" validate')
    copy_at = installer.index('sudo -n install -o root -g root -m 0644 "$service_source"')
    assert validate_at < copy_at
    assert 'git -C "$candidate_worktree" status --porcelain' in installer
    assert installer.index('status --porcelain') < copy_at
    assert "trap rollback EXIT" in installer
    assert "install_complete=0" in installer
    assert 'sudo -n rm -f "$service_target"' in installer
    assert 'sudo -n rm -f "$include_target"' in installer
    assert 'sudo -n install -o root -g root -m 0644 "$edge_backup" "$edge_config"' in installer
    assert 'sudo -n systemctl disable "$service_name"' in installer
    assert "openresty -t" in installer
    assert installer.index("openresty -t") < installer.index('systemctl restart "$service_name"')


def test_beta_installer_revalidates_and_reloads_restored_edge_after_reload_failure():
    installer = Path("scripts/install_oci_beta.sh").read_text(encoding="utf-8")
    reload_command = 'sudo -n /usr/local/bin/reload-openresty-1panel.sh'

    assert "edge_reload_attempted=0" in installer
    assert "edge_reload_attempted=1" in installer
    assert 'if [[ "$edge_reload_attempted" == 1 && "$edge_restored" == 1 ]]; then' in installer
    assert installer.count(reload_command) >= 2
    restore_at = installer.index('sudo -n install -o root -g root -m 0644 "$edge_backup" "$edge_config"')
    rollback_reload_at = installer.index(reload_command, restore_at)
    assert installer.index('"$edge_helper" validate', restore_at) < rollback_reload_at
    assert installer.index("openresty -t", restore_at) < rollback_reload_at
    assert "hermes-chatgpt-mcp.service" not in installer


def test_beta_installer_rollback_tracks_failures_and_revalidates_every_restored_boundary():
    installer = Path("scripts/install_oci_beta.sh").read_text(encoding="utf-8")
    rollback = installer[installer.index("rollback() {"): installer.index("trap rollback EXIT")]

    assert "rollback_failed=0" in installer
    assert "rollback_error()" in installer
    assert "rollback_error \"service" in rollback
    assert "rollback_error \"include" in rollback
    assert "rollback_error \"edge" in rollback
    assert "rollback_error \"environment" in rollback
    assert "rollback_error \"state" in rollback
    assert "cmp -s" in rollback
    assert '"$edge_helper" validate' in rollback
    assert "openresty -t" in rollback
    assert "rollback reload" in rollback
    assert 'if [[ "$rollback_failed" == 1 ]]; then' in rollback
    assert 'exit_status=1' in rollback
    assert "rollback incomplete" in rollback
    assert "|| true" not in rollback


@pytest.mark.parametrize("listen", ["listen 443;\n", "listen 80 ssl;\n", "listen 8443 ssl;\n"])
def test_beta_edge_requires_a_direct_tls_listener_on_port_443(listen):
    with pytest.raises(EdgeConfigError, match="TLS|443"):
        render_edge_config(
            _beta_edge(listen=listen),
            include_path=BETA_INCLUDE,
            hostname=BETA_HOSTNAME,
        )


def test_beta_installer_rejects_an_environment_file_override():
    installer = Path("scripts/install_oci_beta.sh").read_text(encoding="utf-8")

    assert 'MCP_ENV_FILE overrides are not supported' in installer
    assert 'MCP_ENV_FILE:-/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env' not in installer
    assert 'MCP_ENV_FILE:-' not in installer
