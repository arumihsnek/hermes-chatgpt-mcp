#!/usr/bin/env bash
set -Eeuo pipefail

candidate_worktree="/home/ubuntu/code/hermes-chatgpt-mcp/.worktrees/hermes-chatgpt-mcp-beta"
service_name="hermes-chatgpt-mcp-beta.service"
service_source="$candidate_worktree/deploy/systemd/$service_name"
include_source="$candidate_worktree/deploy/openresty/kanban-mcp-beta.conf"
edge_helper="$candidate_worktree/scripts/oci_beta_edge.py"
service_target="/etc/systemd/system/$service_name"
include_dir="/opt/1panel/apps/openresty/openresty/conf/conf.d"
include_target="$include_dir/hermes-chatgpt-mcp-beta.locations"
include_inside="/usr/local/openresty/nginx/conf/conf.d/hermes-chatgpt-mcp-beta.locations"
default_env_file="/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env"
state_dir="/var/lib/hermes-chatgpt-mcp-beta"
edge_config="${MCP_OPENRESTY_CONF:-/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-subdomains.conf}"
marker_begin="# BEGIN hermes-chatgpt-mcp-beta managed include"
marker_end="# END hermes-chatgpt-mcp-beta managed include"
beta_hostname="kanban-beta.hermesinthenight.duckdns.org"

if [[ ${MCP_ENV_FILE+x} == x && "$MCP_ENV_FILE" != "$default_env_file" ]]; then
    echo "MCP_ENV_FILE overrides are not supported; use $default_env_file" >&2
    exit 1
fi
env_file="$default_env_file"

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <beta-commit>" >&2
    exit 2
fi
requested_commit="$1"

if ! git -C "$candidate_worktree" worktree list --porcelain | awk -v target="$candidate_worktree" '
    $1 == "worktree" && $2 == target { found = 1 }
    END { exit !found }
'; then
    echo "candidate path is not the required Git worktree: $candidate_worktree" >&2
    exit 1
fi
candidate_commit="$(git -C "$candidate_worktree" rev-parse HEAD)"
requested_commit="$(git -C "$candidate_worktree" rev-parse --verify "${requested_commit}^{commit}")"
if [[ "$requested_commit" != "$candidate_commit" ]]; then
    echo "candidate worktree is not at requested beta commit" >&2
    exit 1
fi

require_clean_worktree() {
    if [[ -n "$(git -C "$candidate_worktree" status --porcelain)" ]]; then
        echo "candidate worktree has tracked or untracked changes" >&2
        exit 1
    fi
}

require_clean_worktree

if ! sudo -n true 2>/dev/null; then
    echo "passwordless sudo is required for OCI installation" >&2
    exit 1
fi
if [[ ! -f "$service_source" || ! -f "$include_source" || ! -f "$edge_helper" ]]; then
    echo "beta deployment files are missing from $candidate_worktree" >&2
    exit 1
fi
if [[ ! -f "$edge_config" ]]; then
    echo "OpenResty configuration not found: $edge_config" >&2
    exit 1
fi
if [[ -n "${MCP_OPENRESTY_CONTAINER:-}" ]]; then
    openresty_container="$MCP_OPENRESTY_CONTAINER"
else
    openresty_container="$(sudo -n ctr -n moby containers list 2>/dev/null | awk '/1panel\/openresty/ {print $1; exit}')"
fi
if [[ -z "$openresty_container" ]]; then
    echo "running 1Panel OpenResty container was not found" >&2
    exit 1
fi

# This is read-only and deliberately happens before any service, include,
# edge, state, or environment-file mutation.
sudo -n /usr/bin/python3 "$edge_helper" validate \
    --edge "$edge_config" --include "$include_inside" --hostname "$beta_hostname"

# Recheck immediately before the first artifact copy so a change made during
# preflight cannot be promoted by this installer.
require_clean_worktree

rollback_dir=""
install_complete=0
mutation_started=0
service_was_present=0
service_was_enabled=0
service_was_active=0
service_started_by_installer=0
edge_reload_attempted=0
edge_restored=0
include_was_present=0
edge_was_present=0
env_was_present=0
state_dir_was_present=0
service_backup=""
include_backup=""
edge_backup=""
env_backup=""
rollback_failed=0
rollback_errors=()

rollback_error() {
    rollback_failed=1
    rollback_errors+=("$1")
}

rollback() {
    local exit_status=$?
    set +e
    trap - EXIT
    if [[ "$mutation_started" == 1 && "$install_complete" == 0 ]]; then
        if [[ "$service_started_by_installer" == 1 ]]; then
            if ! sudo -n systemctl stop "$service_name" 2>/dev/null; then
                rollback_error "service stop"
            fi
        fi
        if [[ "$service_was_present" == 0 ]]; then
            if ! sudo -n systemctl disable "$service_name" 2>/dev/null; then
                rollback_error "service disable"
            fi
        elif [[ "$service_was_enabled" == 0 ]]; then
            if ! sudo -n systemctl disable "$service_name" 2>/dev/null; then
                rollback_error "service disable"
            fi
        fi

        if [[ "$service_was_present" == 1 ]]; then
            if ! sudo -n install -o root -g root -m 0644 "$service_backup" "$service_target"; then
                rollback_error "service restore"
            fi
        else
            if ! sudo -n rm -f "$service_target"; then
                rollback_error "service removal"
            fi
        fi
        if [[ "$include_was_present" == 1 ]]; then
            if ! sudo -n install -o root -g root -m 0644 "$include_backup" "$include_target"; then
                rollback_error "include restore"
            fi
        else
            if ! sudo -n rm -f "$include_target"; then
                rollback_error "include removal"
            fi
        fi
        if [[ "$edge_was_present" == 1 ]]; then
            if sudo -n install -o root -g root -m 0644 "$edge_backup" "$edge_config"; then
                edge_restored=1
            else
                rollback_error "edge restore"
            fi
        else
            if sudo -n rm -f "$edge_config"; then
                edge_restored=1
            else
                rollback_error "edge removal"
            fi
        fi

        if [[ "$env_was_present" == 1 ]]; then
            if ! sudo -n install -o ubuntu -g ubuntu -m 0600 "$env_backup" "$env_file"; then
                rollback_error "environment restore"
            fi
        else
            if ! sudo -n rm -f "$env_file"; then
                rollback_error "environment removal"
            fi
        fi
        if [[ "$state_dir_was_present" == 0 ]]; then
            if ! sudo -n rm -rf -- "$state_dir"; then
                rollback_error "state removal"
            fi
        fi
        if ! sudo -n systemctl daemon-reload 2>/dev/null; then
            rollback_error "systemd reload"
        fi

        if [[ "$service_was_present" == 1 ]]; then
            if ! sudo -n test -f "$service_target" || ! sudo -n cmp -s "$service_backup" "$service_target"; then
                rollback_error "service revalidation"
            fi
        elif sudo -n test -e "$service_target"; then
            rollback_error "service absence revalidation"
        fi
        if [[ "$include_was_present" == 1 ]]; then
            if ! sudo -n test -f "$include_target" || ! sudo -n cmp -s "$include_backup" "$include_target"; then
                rollback_error "include revalidation"
            fi
        elif sudo -n test -e "$include_target"; then
            rollback_error "include absence revalidation"
        fi
        if [[ "$env_was_present" == 1 ]]; then
            if ! sudo -n test -f "$env_file" || ! sudo -n cmp -s "$env_backup" "$env_file"; then
                rollback_error "environment revalidation"
            fi
        elif sudo -n test -e "$env_file"; then
            rollback_error "environment absence revalidation"
        fi
        if [[ "$state_dir_was_present" == 1 ]]; then
            if ! sudo -n test -d "$state_dir"; then
                rollback_error "state revalidation"
            fi
        elif sudo -n test -e "$state_dir"; then
            rollback_error "state absence revalidation"
        fi
        if [[ "$edge_was_present" == 1 ]]; then
            if ! sudo -n test -f "$edge_config" || ! sudo -n cmp -s "$edge_backup" "$edge_config"; then
                rollback_error "edge revalidation"
            fi
        elif sudo -n test -e "$edge_config"; then
            rollback_error "edge absence revalidation"
        fi
        if [[ "$edge_was_present" == 1 && "$edge_restored" == 1 ]]; then
            if ! sudo -n /usr/bin/python3 "$edge_helper" validate \
                --edge "$edge_config" --include "$include_inside" --hostname "$beta_hostname"; then
                rollback_error "edge semantic revalidation"
            fi
            rollback_exec_id="hermes-chatgpt-mcp-beta-rollback-syntax-$(date +%s)"
            if ! sudo -n ctr -n moby tasks exec --exec-id "$rollback_exec_id" "$openresty_container" \
                /usr/local/openresty/bin/openresty -t -c /usr/local/openresty/nginx/conf/nginx.conf; then
                rollback_error "edge syntax revalidation"
            fi
        fi
        if [[ "$edge_reload_attempted" == 1 && "$edge_restored" == 1 ]]; then
            if ! sudo -n /usr/local/bin/reload-openresty-1panel.sh; then
                rollback_error "rollback reload"
            fi
        fi
        if [[ "$service_was_active" == 1 ]]; then
            if ! sudo -n systemctl start "$service_name" 2>/dev/null; then
                rollback_error "service restart"
            fi
        fi
        if [[ "$service_was_active" == 1 ]]; then
            if ! sudo -n systemctl is-active --quiet "$service_name"; then
                rollback_error "service active-state revalidation"
            fi
        elif sudo -n systemctl is-active --quiet "$service_name"; then
            rollback_error "service inactive-state revalidation"
        fi
        if [[ "$service_was_enabled" == 1 ]]; then
            if ! sudo -n systemctl is-enabled --quiet "$service_name"; then
                rollback_error "service enabled-state revalidation"
            fi
        elif sudo -n systemctl is-enabled --quiet "$service_name"; then
            rollback_error "service disabled-state revalidation"
        fi
    fi
    if [[ -n "$rollback_dir" ]]; then
        if ! sudo -n rm -rf -- "$rollback_dir" 2>/dev/null; then
            rollback_error "rollback cleanup"
        fi
    fi
    if [[ "$rollback_failed" == 1 ]]; then
        echo "beta rollback incomplete; safe diagnostic: ${rollback_errors[*]}" >&2
        exit_status=1
    fi
    exit "$exit_status"
}
trap rollback EXIT

rollback_dir="$(sudo -n mktemp -d -p /run hermes-chatgpt-mcp-beta-install.XXXXXX)"
sudo -n chmod 0700 "$rollback_dir"
service_backup="$rollback_dir/service"
include_backup="$rollback_dir/include"
edge_backup="$rollback_dir/edge"
env_backup="$rollback_dir/env"

if sudo -n test -e "$service_target"; then
    service_was_present=1
    sudo -n cp -- "$service_target" "$service_backup"
fi
if sudo -n systemctl is-enabled --quiet "$service_name"; then
    service_was_enabled=1
fi
if sudo -n systemctl is-active --quiet "$service_name"; then
    service_was_active=1
fi
if sudo -n test -e "$include_target"; then
    include_was_present=1
    sudo -n cp -- "$include_target" "$include_backup"
fi
if sudo -n test -e "$edge_config"; then
    edge_was_present=1
    sudo -n cp -- "$edge_config" "$edge_backup"
fi
if sudo -n test -e "$env_file"; then
    env_was_present=1
    sudo -n cp -- "$env_file" "$env_backup"
fi
if sudo -n test -d "$state_dir"; then
    state_dir_was_present=1
fi

# Backups are read-only with respect to the deployment targets; check again
# immediately before the first artifact copy after that preflight window.
require_clean_worktree

mutation_started=1
sudo -n install -o root -g root -m 0644 "$service_source" "$service_target"
sudo -n install -d -o root -g root -m 0755 "$include_dir"
sudo -n install -o root -g root -m 0644 "$include_source" "$include_target"
sudo -n /usr/bin/python3 "$edge_helper" apply \
    --edge "$edge_config" --include "$include_inside" --hostname "$beta_hostname"

exec_id="hermes-chatgpt-mcp-beta-syntax-$(date +%s)"
sudo -n ctr -n moby tasks exec --exec-id "$exec_id" "$openresty_container" \
    /usr/local/openresty/bin/openresty -t -c /usr/local/openresty/nginx/conf/nginx.conf

sudo -n install -d -o ubuntu -g ubuntu -m 0700 "$state_dir"
env_parent="$(dirname "$env_file")"
sudo -n install -d -o ubuntu -g ubuntu -m 0700 "$env_parent"
sudo -n -u ubuntu /usr/bin/python3 - "$env_file" <<'PY'
from __future__ import annotations

import secrets
import sys
from pathlib import Path

path = Path(sys.argv[1])
values: dict[str, str] = {}
if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), value.strip())

values.setdefault("MCP_OAUTH_USERNAME", "chatgpt")
values.setdefault("MCP_OAUTH_PASSWORD", secrets.token_urlsafe(24))
values.setdefault("MCP_OAUTH_SIGNING_KEY", secrets.token_urlsafe(48))
values.update(
    {
        "HERMES_AGENT_ROOT": "/home/ubuntu/hermes-agent",
        "HERMES_KANBAN_HOME": "/home/ubuntu/.hermes",
        "MCP_PUBLIC_BASE_URL": "https://kanban-beta.hermesinthenight.duckdns.org",
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": "8791",
        "MCP_SURFACE": "beta",
        "MCP_BOARD_CREATE_ENABLED": "1",
        "MCP_OAUTH_STATE_FILE": "/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json",
    }
)
ordered = [
    "HERMES_AGENT_ROOT", "HERMES_KANBAN_HOME", "MCP_PUBLIC_BASE_URL", "MCP_HOST", "MCP_PORT",
    "MCP_SURFACE", "MCP_BOARD_CREATE_ENABLED", "MCP_OAUTH_USERNAME", "MCP_OAUTH_PASSWORD",
    "MCP_OAUTH_SIGNING_KEY", "MCP_OAUTH_STATE_FILE",
]
extra = [key for key in values if key not in ordered]
path.write_text("".join(f"{key}={values[key]}\n" for key in ordered + extra), encoding="utf-8")
path.chmod(0o600)
PY
sudo -n chown ubuntu:ubuntu "$env_file"
sudo -n chmod 0600 "$env_file"

# Install the beta package into the dedicated venv so the running service
# picks up the current worktree source (editable = live source).
sudo -n /opt/venvs/hermes-chatgpt-mcp/bin/pip install -e "$candidate_worktree" --quiet

sudo -n systemctl daemon-reload
sudo -n systemctl enable "$service_name"
service_started_by_installer=1
sudo -n systemctl restart "$service_name"
sudo -n systemctl is-active --quiet "$service_name"

healthy=0
for _ in $(seq 1 20); do
    if /opt/venvs/hermes-chatgpt-mcp/bin/python - <<'PY'
import http.client

try:
    connection = http.client.HTTPConnection("127.0.0.1", 8791, timeout=1)
    connection.request("GET", "/healthz")
    response = connection.getresponse()
    healthy = response.status == 200 and response.read(128) == b'{"status":"ok"}'
except OSError:
    healthy = False
raise SystemExit(0 if healthy else 1)
PY
    then
        healthy=1
        break
    fi
    sleep 1
done
if [[ "$healthy" != 1 ]]; then
    echo "beta MCP loopback health check failed" >&2
    sudo -n systemctl status "$service_name" --no-pager >&2 || true
    exit 1
fi

edge_reload_attempted=1
sudo -n /usr/local/bin/reload-openresty-1panel.sh

install_complete=1
echo "Installed $service_name at requested beta commit $candidate_commit."
echo "Runtime credentials are stored in $env_file (not printed)."
