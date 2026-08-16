#!/usr/bin/env python3
"""Exercise the deployed MCP surface against two explicitly controlled boards.

Read checks are the default. Set ``HERMES_LIVE_WRITE_TEST=1`` only for one
clearly-prefixed create per board. Each write uses a separate board-bound
grant, mirroring separate authorized sessions; cleanup uses Hermes' native
archive/delete functions and never a public MCP delete operation.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.hermes import load_kanban_module


def _rpc(client: httpx.Client, token: str, method: str, params: dict, request_id: int) -> dict:
    response = client.post(
        "/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("isError"):
        raise RuntimeError(f"MCP operation failed: {method}")
    return result


def _cleanup(settings: Settings, created: dict[str, str]) -> None:
    hermes = load_kanban_module(settings.hermes_agent_root)
    for slug, task_id in created.items():
        db_path = Path(hermes.kanban_db_path(board=slug)).resolve()
        with hermes.connect_closing(db_path=db_path, board=slug) as conn:
            if not hermes.archive_task(conn, task_id):
                raise RuntimeError(f"cleanup could not archive live smoke task on {slug}")
            if not hermes.delete_archived_task(conn, task_id):
                raise RuntimeError(f"cleanup could not delete live smoke task on {slug}")


def main() -> int:
    if os.environ.get("HERMES_LIVE_TEST") != "1":
        raise SystemExit("refusing live smoke without HERMES_LIVE_TEST=1")
    settings = Settings.from_env()
    boards = tuple(filter(None, (os.environ.get("MCP_LIVE_TEST_BOARDS", "codex_app_server,dashboard").split(","))))
    if len(boards) != 2 or len(set(boards)) != 2:
        raise SystemExit("MCP_LIVE_TEST_BOARDS must contain exactly two distinct boards")
    endpoint = os.environ.get("MCP_LIVE_URL", f"{settings.public_base_url}/mcp")
    auth = AuthService(settings)
    read_token = auth.issue_access_token(
        client_id="live-multiboard-smoke",
        subject="live-multiboard-smoke",
        scopes=["hermes:read"],
    )
    write_tokens = {
        slug: auth.issue_access_token(
            client_id=f"live-multiboard-smoke-{slug}",
            subject="live-multiboard-smoke",
            scopes=["hermes:read", "hermes:create"],
            board=slug,
            board_access="write",
        )
        for slug in boards
    }
    created: dict[str, str] = {}
    nonce = secrets.token_hex(6)
    try:
        with httpx.Client(base_url=endpoint.removesuffix("/mcp"), timeout=20.0) as client:
            tools = _rpc(client, read_token, "tools/list", {}, 1)["tools"]
            names = {tool["name"] for tool in tools}
            expected = {
                "list_boards", "get_board", "list_tasks", "get_task",
                "get_task_graph", "get_dispatch", "get_activity", "create_task",
            }
            if names != expected:
                raise RuntimeError(f"unexpected MCP tool surface: {sorted(names)}")
            discovered = _rpc(client, read_token, "tools/call", {"name": "list_boards", "arguments": {}}, 2)
            discovered_slugs = {item["slug"] for item in discovered["structuredContent"]["items"]}
            if not set(boards).issubset(discovered_slugs):
                raise RuntimeError("configured live boards were not discoverable")
            for index, slug in enumerate(boards, start=10):
                board = _rpc(client, read_token, "tools/call", {"name": "get_board", "arguments": {"request": {"board": slug}}}, index)
                if board["structuredContent"]["slug"] != slug:
                    raise RuntimeError(f"board resolver crossed boundary for {slug}")
                tasks = _rpc(client, read_token, "tools/call", {"name": "list_tasks", "arguments": {"request": {"board": slug, "limit": 1}}}, index + 10)
                print(f"PASS read board={slug} tasks={len(tasks['structuredContent']['items'])}")
            if os.environ.get("HERMES_LIVE_WRITE_TEST") != "1":
                print("PASS discovery/read-only multi-board smoke; writes not requested")
                return 0
            for index, slug in enumerate(boards, start=30):
                key = f"chatgpt-mcp-v04-smoke-{slug}-{nonce}"
                write_token = write_tokens[slug]
                result = _rpc(client, write_token, "tools/call", {"name": "create_task", "arguments": {"request": {
                    "board": slug,
                    "title": f"[mcp-v04-smoke {nonce}] cleanup required",
                    "body": "Temporary verification card; delete only through native cleanup.",
                    "idempotency_key": key,
                }}}, index)
                payload = result["structuredContent"]
                if payload["board"] != slug:
                    raise RuntimeError(f"create_task crossed board boundary for {slug}")
                created[slug] = payload["task_id"]
                retry = _rpc(client, write_token, "tools/call", {"name": "create_task", "arguments": {"request": {
                    "board": slug, "title": "retry", "idempotency_key": key,
                }}}, index + 1)
                if retry["structuredContent"]["task_id"] != payload["task_id"]:
                    raise RuntimeError(f"idempotency failed on {slug}")
                _rpc(client, write_token, "tools/call", {"name": "get_task", "arguments": {"request": {
                    "board": slug, "task_id": payload["task_id"],
                }}}, index + 2)
                _rpc(client, write_token, "tools/call", {"name": "get_activity", "arguments": {"request": {
                    "board": slug, "task_id": payload["task_id"], "max_items": 20, "log_bytes": 0,
                }}}, index + 3)
                _rpc(client, write_token, "tools/call", {"name": "get_dispatch", "arguments": {"request": {
                    "board": slug, "task_id": payload["task_id"],
                }}}, index + 4)
                print(f"PASS write board={slug} task={payload['task_id']} idempotent=true")
    finally:
        if created:
            _cleanup(settings, created)
            print(f"PASS native cleanup boards={','.join(sorted(created))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
