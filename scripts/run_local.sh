#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
exec "${PYTHON:-/home/ubuntu/hermes-agent/venv/bin/python}" -m hermes_chatgpt_mcp.server
