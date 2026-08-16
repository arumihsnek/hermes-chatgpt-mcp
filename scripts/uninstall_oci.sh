#!/usr/bin/env bash
set -euo pipefail

service_name="hermes-chatgpt-mcp.service"
service_target="/etc/systemd/system/$service_name"
include_dir="/opt/1panel/apps/openresty/openresty/conf/conf.d"
include_target="$include_dir/hermes-chatgpt-mcp.locations"
env_file="${MCP_ENV_FILE:-/home/ubuntu/.hermes/hermes-chatgpt-mcp.env}"
edge_config="${MCP_OPENRESTY_CONF:-/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-subdomains.conf}"
marker_begin="# BEGIN hermes-chatgpt-mcp managed include"
marker_end="# END hermes-chatgpt-mcp managed include"

if ! sudo -n true 2>/dev/null; then
    echo "passwordless sudo is required for OCI uninstall" >&2
    exit 1
fi

sudo -n systemctl disable --now "$service_name" 2>/dev/null || true
sudo -n rm -f "$service_target" "$include_target"
if [[ -f "$edge_config" ]]; then
    sudo -n /usr/bin/python3 - "$edge_config" "$marker_begin" "$marker_end" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
begin = sys.argv[2]
end = sys.argv[3]
text = path.read_text(encoding="utf-8")
start = text.find(begin)
if start >= 0:
    finish = text.find(end, start)
    if finish < 0:
        raise SystemExit("managed OpenResty marker is incomplete")
    finish = text.find("\n", finish)
    if finish < 0:
        finish = len(text)
    else:
        finish += 1
    path.write_text(text[:start] + text[finish:], encoding="utf-8")
PY
fi
sudo -n systemctl daemon-reload
sudo -n /usr/local/bin/reload-openresty-1panel.sh 2>/dev/null || true
echo "Removed the integration service and its managed edge include."
echo "The runtime environment file was preserved at $env_file for recovery/audit."
