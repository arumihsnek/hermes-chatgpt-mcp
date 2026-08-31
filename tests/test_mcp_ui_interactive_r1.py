from __future__ import annotations

from pathlib import Path

from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.server import _build_primary_kanban_ui, _widget_resource_meta
from hermes_chatgpt_mcp.ui import (
    KANBAN_UI_HTML_INTERACTIVE_R1,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R1,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R14,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16,
    KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162,
    build_kanban_ui_interactive_r1_html,
)


def test_widget_resource_meta_declares_domain_and_empty_inline_csp():
    meta = _widget_resource_meta(
        public_base_url="https://kanban-canary.hermesinthenight.duckdns.org/path/ignored",
        version="interactive-r1.6",
    )
    assert meta == {
        "ui": {
            "domain": "https://kanban-canary.hermesinthenight.duckdns.org",
            "csp": {"connectDomains": [], "resourceDomains": []},
        },
        "version": "interactive-r1.6",
    }


def test_primary_cached_uri_keeps_legacy_ui_when_flag_is_off():
    html = _build_primary_kanban_ui(interactive=False)
    assert 'data-ui-version="interactive-r1.6.2"' not in html


def test_primary_cached_uri_serves_current_interactive_ui_when_flag_is_on():
    html = _build_primary_kanban_ui(interactive=True)
    assert 'data-ui-version="interactive-r1.6.2"' in html
    assert 'id="status-strip"' in html
    assert 'id="board-viewport"' in html
    assert 'id="inspector-dialog"' in html
    assert 'id="pending-bar"' in html


def test_interactive_resource_is_bounded_and_named():
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


def test_interactive_r16_has_its_own_fresh_tool_and_resource_binding():
    assert KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16 == "ui://hermes/kanban/interactive-r16-ux"
    source = (Path(__file__).parents[1] / "hermes_chatgpt_mcp" / "server.py").read_text(encoding="utf-8")
    assert 'name="get_board_interactive_r16"' in source
    assert 'resourceUri": KANBAN_UI_RESOURCE_URI_INTERACTIVE_R16' in source
    assert 'name="hermes_kanban_ui_interactive_r16"' in source
    assert 'version="interactive-r1.6-r16"' in source


def test_interactive_r16_uses_only_allowlisted_canonical_mutations():
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
        "list_boards",
        "list_tasks",
        "get_task",
        "get_task_graph",
    ):
        assert f"'{tool}'" in html

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
        assert forbidden not in html


def test_interactive_r16_bridge_matches_mcp_apps_request_response_pattern():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "const pendingRequests=new Map()" in html
    assert "window.parent.postMessage({jsonrpc:'2.0',id,method,params},'*')" in html
    assert "event.source!==window.parent" in html
    assert "message.jsonrpc!=='2.0'" in html
    assert "message.id!==undefined&&pendingRequests.has(message.id)" in html
    assert "pending.resolve(message.result)" in html
    assert "request('tools/call',{name,arguments:args||{}})" in html
    assert "timed out waiting for MCP Apps host" in html


def test_interactive_r16_has_bounded_external_reconciliation():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "LIVE_INTERVAL_MS=3000" in html
    assert "MAX_LIVE_CYCLES=20" in html
    assert "LIVE_MAX_MS=60000" in html
    assert "document.hidden" in html
    assert "visibilitychange" in html
    assert "unload" in html
    assert "clearInterval" in html


def test_interactive_r16_never_treats_staging_as_canonical_success():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "Nothing mutates Hermes until Confirm." in html
    assert "staged · Confirm to mutate Hermes." in html
    assert "await tool(a.tool,a.args)" in html
    assert "await refreshBoard()" in html
    assert "Confirmed actions reconciled from canonical board." in html


def test_interactive_r16_status_toggles_are_full_width_and_columns_scroll_separately():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert ".status-strip{display:grid;grid-template-columns:repeat(8,minmax(0,1fr))" in html
    assert ".status-strip" in html and "overflow:visible" in html
    assert ".board-viewport{width:100%;overflow-x:auto" in html
    assert 'id="board-viewport"' in html
    assert 'id="board-columns"' in html
    assert "visible:{todo:true,ready:true,running:true}" in html


def test_interactive_r16_inspector_is_modal_not_bottom_panel():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert '<dialog id="inspector-dialog">' in html
    assert "dialog.showModal()" in html
    assert "dialog.close()" in html
    assert 'class="modal-body"' in html
    assert ".layout{" not in html


def test_interactive_r16_drag_drop_stages_before_confirm():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "card.draggable=true" in html
    assert "card.ondragstart" in html
    assert "col.ondragover" in html
    assert "col.ondrop" in html
    assert "function canDrop(task,target)" in html
    assert "function transitionAction(task,target)" in html
    assert "target==='blocked'" in html
    assert "target==='review'" in html
    assert "stageTouchDrop(state.dragTask,k);clearDropTargets()" in html
    assert "canDropDrag(state.dragTask,k)" in html


def test_interactive_r16_staged_move_projects_card_into_destination_column():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "function projectedTasks()" in html
    assert "out[k].splice(ix,1)[0]" in html
    assert "out[a.targetStatus]" in html
    assert "Pending → " in html
    assert "from '+LABEL[t._origin]" in html


def test_interactive_r16_parent_and_child_dependencies_are_distinct():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "kind:'parent'" in html
    assert "kind:'child'" in html
    assert "dep-parent" in html
    assert "dep-child" in html
    assert "'↑'+v.parent" in html
    assert "'↓'+v.child" in html




def test_interactive_r16_regresses_scroll_refresh_and_dependency_badges():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "let boardScrollLeft" in html
    assert "saveBoardScroll();" in html
    assert "restoreBoardScroll()" in html
    assert "refreshing:false" in html
    assert "Refreshing canonical board" in html
    assert "refreshButton.disabled=true" in html
    assert "dep-parent-badge" in html and "dep-child-badge" in html
    assert "Parent dependencies" in html and "Child dependencies" in html
    assert "dependencyCounts(t)" in html


def test_interactive_r16_columns_have_semantic_status_tints():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    assert "background:var(--status-bg,var(--soft))" in html
    for status_name in ("triage", "todo", "ready", "running", "blocked", "review", "scheduled", "done"):
        assert f"status-{status_name}" in html
    assert "--parent" in html and "--child" in html


def test_interactive_r16_preserves_create_comment_assign_and_review_controls():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    for text in (
        "New card", "Create", "Comment", "Assign",
        "Block", "Review", "Unblock", "Changes",
        "Reopen review",
    ):
        assert text in html


def test_interactive_r1_flag_defaults_off():
    assert Settings.__dataclass_fields__["ui_interactive_r1"].default is False

def test_interactive_r1_flag_parses_from_env(monkeypatch):
    monkeypatch.setenv("HERMES_AGENT_ROOT", "/home/ubuntu/hermes-agent")
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "a" * 24)
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "b" * 48)
    monkeypatch.setenv("UI_INTERACTIVE_R1", "true")
    assert Settings.from_env().ui_interactive_r1 is True


def test_interactive_r162_has_fresh_binding_and_mobile_workbench_contract():
    assert KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162 == "ui://hermes/kanban/interactive-r162-mobile-workbench"
    source = (Path(__file__).parents[1] / "hermes_chatgpt_mcp" / "server.py").read_text(encoding="utf-8")
    assert 'name="get_board_interactive_r162"' in source
    assert 'resourceUri": KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162' in source
    assert 'name="hermes_kanban_ui_interactive_r162"' in source
    assert 'interactive-r1.6.2-r162' in source
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    for marker in ("pointerdown", "pointermove", "pointerup", "pointercancel", "setPointerCapture", "420", "dist>10", "dist>8", "requestAnimationFrame", "const step=16"):
        assert marker in html
    assert "window.addEventListener('blur'" in html
    assert "e.key==='Escape'" in html
    assert "eligible '+eligible.length+' / skipped '+skipped" in html
    assert "state.multiSelected" in html and "Clear selection" in html
    assert "applyDependencyHighlight(state.selected)" in html
    assert "kind:'manual'" not in html
    assert "kind:'needs_input'" in html
    assert 'data-ui-version="interactive-r1.6.2"' in html
    assert "applyDependencyHighlight(state.selected||id)" in html
    assert "function canDropDrag(task,target)" in html and "tasks.every(x=>canDrop(x,target))" in html
    assert "const skipped=ids.length-eligible.length" in html
    assert "cancelAnimationFrame" in html and "touchAutoScrollFrame" in html
    assert "card.draggable=false" in html and "card.draggable=true" in html
    assert "KANBAN_UI_RESOURCE_URI_INTERACTIVE_R162 if (settings.ui_interactive_r1 and settings.chatgpt_compat_mode)" in source


def test_interactive_r162_toggle_contrast_is_explicit_in_light_and_dark():
    html = KANBAN_UI_HTML_INTERACTIVE_R1
    for marker in ("--toggle-bg", "--toggle-fg", "--toggle-active-bg", "--toggle-active-fg"):
        assert marker in html
    assert "@media(prefers-color-scheme:dark)" in html
    for status_name in ("triage", "todo", "ready", "running", "blocked", "review", "scheduled", "done"):
        assert f".kanban-column.status-{status_name}" in html
    assert "background:var(--status-bg,#202124)" in html
