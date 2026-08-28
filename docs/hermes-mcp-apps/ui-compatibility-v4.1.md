# MCP Apps UI compatibility (V4.1 rolling forward-port)

The rolling baseline keeps its canonical 22-tool surface and Human Gate names. In particular, Human Gate readback is exposed as `human-gate` (and decisions as `human-gate-decide` on the beta surface); the legacy `get_human_gate_readback` name is not restored.

## Resource discovery

`resources/list` advertises these resources:

| URI | MIME type | Default | Purpose |
|---|---|---:|---|
| `ui://hermes/kanban/v1` | `text/html;profile=mcp-app` | yes | Read-only board view |
| `ui://hermes/human-gate/v1` | `text/html;profile=mcp-app` | yes | Non-authoritative Human Gate readback |
| `ui://hermes/kanban/v2` | `text/html;profile=mcp-app` | no | Bounded create-task form; enabled only by `UI_WRITE_ENABLED_V2=true` |

The `get_board` tool carries additive `_meta.ui.resourceUri` metadata pointing to the V1 resource. No existing tool is renamed or removed.

## V2 write boundary

When enabled, V2 accepts only the bounded title/body/parent subset through `UiMutationAdapter`, requires a capability scoped to board and tenant, checks `expected_board_revision`, and records an idempotency receipt. It remains disabled by default. The normal canonical `create_task` path is unchanged while disabled.

`auth.py` is unchanged. `config.py` adds only `UI_WRITE_ENABLED_V2`, defaulting to false; all other rolling settings remain intact.

## Verification snapshot

- UI-focused tests: 30 passed.
- Broad compatibility slice: 86 passed, with the one known unrelated rolling `update_task` idempotency failure reproduced separately.
- `python -m compileall -q hermes_chatgpt_mcp` and `git diff --check` pass.
