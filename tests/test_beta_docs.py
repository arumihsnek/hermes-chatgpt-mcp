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


def test_stable_only_claims_and_beta_board_claim_exception_are_explicit() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    security = (ROOT / "docs/SECURITY.md").read_text(encoding="utf-8")
    integration = (ROOT / "docs/architecture/HERMES-INTEGRATION.md").read_text(
        encoding="utf-8"
    )
    readme = " ".join(readme.split())
    security = " ".join(security.split())
    integration = " ".join(integration.split())

    assert "The stable public surface is seven READ tools plus one WRITE tool:" in readme
    assert "Stable WRITE tool:" in readme
    assert "Every beta board-bound command is checked against the signed OAuth one-board claim" in readme
    assert "The global `create_board` command is the explicit exception" in readme
    assert "Every beta write is checked against the signed OAuth board claim" not in readme
    assert "On the stable surface, the MCP tool allowlist contains exactly eight tools:" in security
    assert "On the stable surface, the create tool is the only public mutator" in integration
    assert "On the stable surface, only `HermesCreateAdapter.create_task`" in integration


def test_beta_dogfood_runbook_defines_release_and_safety_gates() -> None:
    runbook = (ROOT / "docs/BETA_DOGFOOD.md").read_text(encoding="utf-8")

    for marker in (
        "hermes-chatgpt-e2e-20260818t224300z",
        "hermes:create",
        "hermes:manage",
        "hermes:admin",
        "AUTH_READ_ONLY",
        "BLOCKED_PLATFORM",
        "scripts/verify_beta_release.py",
        "notify-subscribe.delivery",
        "do not run",
    ):
        assert marker in runbook, f"missing dogfood release marker: {marker}"
