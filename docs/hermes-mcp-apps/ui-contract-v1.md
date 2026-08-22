# Hermes Kanban MCP Apps UI contract v1

Status: frozen read-only alpha contract, reviewed PASS by task t_e76513cd.

## Canonical seam

- Resource URI: `ui://hermes/kanban/v1`
- MIME type: `text/html;profile=mcp-app`
- Exactly one linked tool: `get_board`, via `_meta.ui.resourceUri`.
- Resource is static, self-contained HTML, at most 262144 UTF-8 bytes.
- Text and structured tool fallback remain mandatory.
- The widget composes only bounded read tools: `list_boards`, `get_board`, `list_tasks`, `get_task`, `get_task_graph`, and `get_dispatch`.
- `get_activity` is intentionally not called by the widget.

## Security and behavior

The view is read-only. It has no write controls, approval controls, model-context updates, external links, storage, or network egress. Dynamic values are created with DOM nodes and `textContent`. A board picker, status columns, card identity, and explicit Refresh control are provided. Refresh uses standard MCP Apps bridge messages and is paused by host visibility through host lifecycle behavior.

The URI is a cache key: behavioral changes require a new versioned URI and tool metadata update in one change set. The stable surface remains bound to `hermes:read`, `hermes:create`, and `offline_access`; no deployment or promotion is part of this alpha.

## Review carry-forward

- Verify the live stable listener's advertised scope set before any dogfood deployment.
- Keep the tighter schema activity bound (`max_items <= 200`, default 100) distinct from the configuration-layer maximum.
- Static purity checks include the zero-tolerance `http://` and `https://` patterns.

## Acceptance evidence

CI runs deterministic registration, MIME, fallback, URI, size, and static-purity tests in `tests/test_mcp_ui_resource.py`. Host-side rendering remains a local reference-harness concern and is not a deployment claim.
