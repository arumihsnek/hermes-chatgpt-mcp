from __future__ import annotations

from pathlib import Path

from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.server import _build_primary_kanban_ui
from hermes_chatgpt_mcp.ui import (
    KANBAN_UI_HTML_INTERACTIVE_R1,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14,
    build_kanban_ui_interactive_r1_html,
)


def test_primary_cached_uri_keeps_legacy_ui_when_interactive_flag_is_off():
    html = _build_primary_kanban_ui(interactive=False)
    assert 'data-ui-version="interactive-r1.1"' not in html


def test_primary_cached_uri_serves_interactive_ui_when_flag_is_on():
    html = _build_primary_kanban_ui(interactive=True)
    assert 'data-ui-version="interactive-r1.1"' in html
    assert 'id="status-strip"' in html
    assert 'id="confirm-bar"' in html
    assert 'function renderColumns()' in html


def test_interactive_r1_resource_is_bounded_and_named():
    html = build_kanban_ui_interactive_r1_html()
    assert KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1 == "ui://hermes/kanban/interactive-r1"
    assert html == KANBAN_UI_HTML_INTERACTIVE_R1
    assert len(html.encode("utf-8")) <= 262_144


def test_interactive_r14_uses_fresh_tool_and_fresh_resource_binding():
    assert KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14 == "ui://hermes/kanban/interactive-r14-fresh-tool"
    source = (Path(__file__).parents[1] / "hermes_chatgpt_mcp" / "server.py").read_text(encoding="utf-8")
    assert 'name="get_board_interactive_r14"' in source
    assert 'resourceUri": KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14' in source
    assert 'name="hermes_kanban_ui_interactive_r14"' in source
    assert 'return build_kanban_ui_interactive_r1_html()' in source


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


def test_interactive_r11_defaults_to_todo_ready_running_columns():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert 'data-ui-version="interactive-r1.1"' in html
    assert 'visible:{todo:true,ready:true,running:true}' in html
    assert 'running:"In progress"' in html
    assert 'id="status-strip"' in html
    assert 'white-space:nowrap' in html
    assert 'overflow-x:auto' in html
    assert 'toggle-count' in html


def test_interactive_r11_stages_actions_before_confirming():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert 'id="confirm-bar"' in html
    assert 'id="confirm-all"' in html
    assert 'id="undo-all"' in html
    assert 'function stageAction(action)' in html
    assert 'function confirmStaged()' in html
    assert 'Action marked — confirm to apply canonical mutation.' in html
    assert 'class="pending-badge"' not in html  # created dynamically, never trusted as static success
    assert 'pending-badge' in html
    assert 'pending-incoming' in html
    assert 'state.staged' in html


def test_interactive_r11_dependency_highlights_visible_and_hidden_columns():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert '"get_task_graph"' in html
    assert 'depth:1,max_nodes:64' in html
    assert 'pointerenter' in html
    assert 'touchstart' in html
    assert 'dep-highlight' in html
    assert 'dep-hidden' in html
    assert 'dep-visible' in html
    assert '↗' in html
    assert 'state.graphs' in html


def test_interactive_r11_renders_cards_inside_status_columns():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert 'id="board-columns"' in html
    assert 'tasksByStatus' in html
    assert 'function loadStatus(k)' in html
    assert 'function renderColumns()' in html
    assert 'grid-auto-columns:minmax(82vw,1fr)' in html
