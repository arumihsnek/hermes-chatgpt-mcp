from __future__ import annotations

from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.ui import (
    KANBAN_UI_HTML_INTERACTIVE_R1,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1,
    build_kanban_ui_interactive_r1_html,
)


def test_interactive_r1_resource_is_bounded_and_named():
    html = build_kanban_ui_interactive_r1_html()
    assert KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1 == "ui://hermes/kanban/interactive-r1"
    assert html == KANBAN_UI_HTML_INTERACTIVE_R1
    assert len(html.encode("utf-8")) <= 262_144


def test_interactive_r1_uses_only_allowlisted_canonical_mutations():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    for tool in (
        "create_task",
        "add_comment",
        "assign_task",
        "block_tasks",
        "unblock_tasks",
        "request_review",
        "request_changes",
        "reopen_review",
        "get_board",
        "list_tasks",
        "get_task",
    ):
        assert f'"{tool}"' in html

    for forbidden in (
        "human-gate-decide",
        "human_gate_decide",
        "complete_tasks",
        "archive_tasks",
        "archive_task",
        "boards-rm",
        "attach-rm",
        "gc",
        "repair",
        "swarm",
        "oauth_revoke",
        "gateway_restart",
    ):
        assert f'"{forbidden}"' not in html


def test_interactive_r1_has_bounded_external_reconciliation():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "LIVE_INTERVAL_MS=3000" in html
    assert "MAX_LIVE_CYCLES=20" in html
    assert "LIVE_MAX_MS=60000" in html
    assert "document.hidden" in html
    assert 'visibilitychange' in html
    assert 'unload' in html
    assert "clearInterval" in html


def test_interactive_r1_never_renders_optimistic_mutation_success():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "canonical readback required" in html.lower()
    assert "reconcile(" in html
    assert 'call("get_task"' in html
    assert 'call("get_board"' in html
    assert 'call("list_tasks"' in html
    assert "Another mutation is in flight" in html


def test_interactive_r1_flag_defaults_off():
    assert Settings.__dataclass_fields__["ui_interactive_r1"].default is False


def test_interactive_r1_flag_parses_from_env(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("UI_INTERACTIVE_R1", "true")
    assert Settings.from_env().ui_interactive_r1 is True
