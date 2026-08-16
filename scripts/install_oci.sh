#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="hermes-chatgpt-mcp.service"
service_source="$repo_root/deploy/systemd/$service_name"
include_source="$repo_root/deploy/openresty/kanban-mcp-locations.conf"
service_target="/etc/systemd/system/$service_name"
include_dir="/opt/1panel/apps/openresty/openresty/conf/conf.d"
include_target="$include_dir/hermes-chatgpt-mcp.locations"
include_inside="/usr/local/openresty/nginx/conf/conf.d/hermes-chatgpt-mcp.locations"
env_file="${MCP_ENV_FILE:-/home/ubuntu/.hermes/hermes-chatgpt-mcp.env}"
edge_config="${MCP_OPENRESTY_CONF:-/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-subdomains.conf}"
marker_begin="# BEGIN hermes-chatgpt-mcp managed include"
marker_end="# END hermes-chatgpt-mcp managed include"

if ! sudo -n true 2>/dev/null; then
    echo "passwordless sudo is required for OCI installation" >&2
    exit 1
fi
if [[ ! -f "$service_source" || ! -f "$include_source" ]]; then
    echo "deployment files are missing from $repo_root" >&2
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
sudo -n install -o root -g root -m 0644 "$include_source" "$include_target"

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
defaults = {
    "HERMES_AGENT_ROOT": "/home/ubuntu/hermes-agent",
    "HERMES_KANBAN_HOME": "/home/ubuntu/.hermes",
    "HERMES_KANBAN_BOARD": "codex_app_server",
    "MCP_PUBLIC_BASE_URL": "https://kanban.hermesinthenight.duckdns.org",
    "MCP_HOST": "127.0.0.1",
    "MCP_PORT": "8789",
    "MCP_OAUTH_USERNAME": "chatgpt",
    "MCP_OAUTH_PASSWORD": secrets.token_urlsafe(24),
    "MCP_OAUTH_SIGNING_KEY": secrets.token_urlsafe(48),
    "MCP_OAUTH_STATE_FILE": "/var/lib/hermes-chatgpt-mcp/oauth-state.json",
}
for key, value in defaults.items():
    values.setdefault(key, value)
ordered = [
    "HERMES_AGENT_ROOT", "HERMES_KANBAN_HOME", "HERMES_KANBAN_BOARD",
    "MCP_PUBLIC_BASE_URL", "MCP_HOST", "MCP_PORT", "MCP_OAUTH_USERNAME",
    "MCP_OAUTH_PASSWORD", "MCP_OAUTH_SIGNING_KEY", "MCP_OAUTH_STATE_FILE",
]
extra = [key for key in values if key not in ordered]
path.write_text("".join(f"{key}={values[key]}\n" for key in ordered + extra), encoding="utf-8")
path.chmod(0o600)
PY
sudo -n chown ubuntu:ubuntu "$env_file"
sudo -n chmod 0600 "$env_file"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
sudo -n /usr/bin/python3 - "$edge_config" "$include_inside" "$timestamp" "$marker_begin" "$marker_end" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

edge = Path(sys.argv[1])
include = sys.argv[2]
timestamp = sys.argv[3]
begin = sys.argv[4]
end = sys.argv[5]
text = edge.read_text(encoding="utf-8")
if begin not in text:
    needle = "server_name kanban.hermesinthenight.duckdns.org;"
    server_name_at = text.find(needle)
    if server_name_at < 0:
        raise SystemExit("kanban HTTPS server block was not found")
    server_start = text.rfind("server {", 0, server_name_at)
    if server_start < 0:
        raise SystemExit("kanban server block start was not found")
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
        raise SystemExit("kanban server block end was not found")
    block = f"\n    {begin}\n    include {include};\n    {end}\n"
    backup = edge.with_name(edge.name + ".bak-hermes-chatgpt-mcp-" + timestamp)
    backup.write_bytes(edge.read_bytes())
    edge.write_text(text[:server_end] + block + text[server_end:], encoding="utf-8")
PY

exec_id="hermes-chatgpt-mcp-syntax-$(date +%s)"
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
    connection = http.client.HTTPConnection("127.0.0.1", 8789, timeout=1)
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
    echo "MCP loopback health check failed" >&2
    sudo -n systemctl status "$service_name" --no-pager >&2 || true
    exit 1
fi

sudo -n /usr/local/bin/reload-openresty-1panel.sh

echo "Installed $service_name and the narrow OpenResty MCP path allowlist."
echo "Runtime credentials are stored in $env_file (not printed)."
