from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from .test_mcp_beta import _beta_app, _rpc, _token


CANONICAL_TO_TOOL = {
    "init": "init", "create": "create_task", "swarm": "swarm", "list": "list_tasks",
    "show": "get_task", "assign": "assign_task", "set-model": "set_model",
    "reclaim": "reclaim_task", "reassign": "reassign_tasks", "diagnostics": "diagnostics",
    "link": "link_tasks", "unlink": "unlink_tasks", "claim": "claim", "comment": "add_comment",
    "attach": "attach", "attachments": "attachments", "attach-rm": "attach-rm",
    "complete": "complete_tasks", "edit": "edit_task", "block": "block_tasks",
    "schedule": "schedule_tasks", "unblock": "unblock_tasks", "request-review": "request_review",
    "request-changes": "request_changes", "reopen-review": "reopen_review", "promote": "promote_tasks",
    "archive": "archive_tasks", "tail": "tail", "dispatch": "dispatch", "daemon": "daemon",
    "watch": "watch", "stats": "stats", "notify-subscribe": "notify-subscribe",
    "notify-list": "notify-list", "notify-unsubscribe": "notify-unsubscribe", "log": "log",
    "runs": "runs", "heartbeat": "heartbeat", "assignees": "assignees", "context": "context",
    "specify": "specify", "decompose": "decompose", "gc": "gc", "repair": "repair",
    "boards list": "list_boards", "boards create": "create_board", "boards rm": "boards-rm",
    "boards switch": "boards-switch", "boards show": "get_board", "boards rename": "boards-rename",
    "boards set-default-workdir": "boards-set-default-workdir",
}


def test_canonical_action_parity_manifest_has_one_tool_mapping():
    assert len(CANONICAL_TO_TOOL) == 51
    assert "boards" not in CANONICAL_TO_TOOL
    assert len(set(CANONICAL_TO_TOOL.values())) == 51


def test_beta_tools_expose_all_canonical_leaf_mappings(tmp_path: Path, monkeypatch):
    async def run():
        fixture, settings, auth, _, app = _beta_app(tmp_path, monkeypatch)
        token = _token(auth, "parity", ["hermes:read", "hermes:manage", "hermes:admin"], board=fixture.board)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=settings.public_base_url) as client:
                result = await _rpc(client, token, "tools/list")
        names = {tool["name"] for tool in result["result"]["tools"]}
        assert set(CANONICAL_TO_TOOL.values()) <= names
        assert all(tool["inputSchema"].get("additionalProperties") is False for tool in result["result"]["tools"])

    asyncio.run(run())
