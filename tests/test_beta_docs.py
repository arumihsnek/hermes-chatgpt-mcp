from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTATION = (
    ROOT / "README.md",
    ROOT / "docs/DEPLOYMENT.md",
    ROOT / "docs/SECURITY.md",
    ROOT / "docs/architecture/HERMES-INTEGRATION.md",
    ROOT / "docs/evidence/BETA-BOARD-MANAGEMENT-PLAN-2026-08-16.md",
)


def _documentation() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in DOCUMENTATION
        if path.exists()
    )


def test_docs_freeze_stable_and_beta_tool_scope_matrices() -> None:
    text = _documentation()

    for marker in (
        "https://kanban.hermesinthenight.duckdns.org/mcp",
        "https://kanban-beta.hermesinthenight.duckdns.org/mcp",
        "127.0.0.1:8789",
        "127.0.0.1:8791",
        "eight tools",
        "eleven tools",
        "hermes:read",
        "hermes:create",
        "hermes:manage",
        "hermes:board:create",
        "offline_access",
        "create_board",
        "add_comment",
        "assign_task",
    ):
        assert marker in text, f"missing beta documentation marker: {marker}"


def test_docs_preserve_stable_behavior_and_one_board_beta_boundary() -> None:
    text = _documentation()

    for marker in (
        "create_board alone does not grant task-write access",
        "BOARD_SESSION_MISMATCH",
        "seq66_looper",
        "MCP_SURFACE=beta",
        "hermes-chatgpt-mcp.service",
        "hermes-chatgpt-mcp-beta.service",
        "/var/lib/hermes-chatgpt-mcp/oauth-state.json",
        "/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json",
        "list_boards",
        "uniquely named",
        "one test card",
        "one comment",
        "assign it",
        "pending",
    ):
        assert marker in text, f"missing stable-preservation/beta-operation marker: {marker}"
