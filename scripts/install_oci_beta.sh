#!/usr/bin/env bash
set -euo pipefail

candidate_worktree="/home/ubuntu/code/hermes-chatgpt-mcp/.worktrees/hermes-chatgpt-mcp-beta"
service_name="hermes-chatgpt-mcp-beta.service"
service_source="$candidate_worktree/deploy/systemd/$service_name"
include_source="$candidate_worktree/deploy/openresty/kanban-mcp-beta.conf"
service_target="/etc/systemd/system/$service_name"
include_dir="/opt/1panel/apps/openresty/openresty/conf/conf.d"
include_target="$include_dir/hermes-chatgpt-mcp-beta.conf"
include_inside="/usr/local/openresty/nginx/conf/conf.d/hermes-chatgpt-mcp-beta.conf"
env_file="${MCP_ENV_FILE:-/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env}"
state_dir="/var/lib/hermes-chatgpt-mcp-beta"
edge_config="${MCP_OPENRESTY_CONF:-/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-subdomains.conf}"
marker_begin="# BEGIN hermes-chatgpt-mcp-beta managed include"
marker_end="# END hermes-chatgpt-mcp-beta managed include"
beta_hostname="kanban-beta.hermesinthenight.duckdns.org"

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
if ! sudo -n true 2>/dev/null; then
    echo "passwordless sudo is required for OCI installation" >&2
    exit 1
fi
if [[ ! -f "$service_source" || ! -f "$include_source" ]]; then
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

sudo -n install -o root -g root -m 0644 "$service_source" "$service_target"
sudo -n install -d -o root -g root -m 0755 "$include_dir"
sudo -n install -o root -g root -m 0644 "$include_source" "$include_target"
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

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
sudo -n /usr/bin/python3 - "$edge_config" "$include_inside" "$timestamp" "$marker_begin" "$marker_end" "$beta_hostname" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

edge = Path(sys.argv[1])
include = sys.argv[2]
timestamp = sys.argv[3]
begin = sys.argv[4]
end = sys.argv[5]
hostname = sys.argv[6]
text = edge.read_text(encoding="utf-8")
if begin not in text:
    needle = f"server_name {hostname};"
    server_name_at = text.find(needle)
    if server_name_at < 0:
        raise SystemExit(f"beta HTTPS server block was not found: {hostname}")
    server_start = text.rfind("server {", 0, server_name_at)
    if server_start < 0:
        raise SystemExit("beta server block start was not found")
    depth = 0
    server_end = None
    for index in range(server_start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                server_end = index
                break
    if server_end is None:
        raise SystemExit("beta server block end was not found")
    backup = edge.with_name(edge.name + ".bak-hermes-chatgpt-mcp-beta-" + timestamp)
    backup.write_bytes(edge.read_bytes())
    block = f"\n    {begin}\n    include {include};\n    {end}\n"
    edge.write_text(text[:server_end] + block + text[server_end:], encoding="utf-8")
PY

exec_id="hermes-chatgpt-mcp-beta-syntax-$(date +%s)"
sudo -n ctr -n moby tasks exec --exec-id "$exec_id" "$openresty_container" \
    /usr/local/openresty/bin/openresty -t -c /usr/local/openresty/nginx/conf/nginx.conf

sudo -n systemctl daemon-reload
sudo -n systemctl enable "$service_name"
sudo -n systemctl restart "$service_name"
sudo -n systemctl is-active --quiet "$service_name"

healthy=0
for _ in $(seq 1 20); do
    if /home/ubuntu/hermes-agent/venv/bin/python - <<'PY'
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

sudo -n /usr/local/bin/reload-openresty-1panel.sh

echo "Installed $service_name at requested beta commit $candidate_commit."
echo "Runtime credentials are stored in $env_file (not printed)."
