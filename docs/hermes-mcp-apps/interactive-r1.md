# MCP Apps Interactive R1 — shared human + ChatGPT control contract

Status: DESIGN_READY candidate
Base: `c257848afec49405a67b09a25fbe7ec2dfd8ecd2`
Branch: `mcp-ui-interactive-r1`

## Goal

Make the Kanban MCP App genuinely bidirectional without creating a second control plane.

- Human actions originate in the MCP App.
- ChatGPT actions originate through the normal Hermes MCP tools.
- Both paths mutate the same canonical Hermes board.
- The UI never treats local state as authoritative.
- A UI action is not rendered as successful until canonical readback confirms it.

The transport is the MCP Apps host bridge (`tools/call` over the existing JSON-RPC postMessage bridge). The UI MUST call the same canonical tool surface exposed to ChatGPT; it MUST NOT introduce a parallel arbitrary-DB mutation API.

## Existing evidence retained

- D2 `t_4f5839a2`: bounded create-only UI seam and idempotency work.
- D3 `t_d460c1cc`: Human Gate remains readback/handoff only; no UI approval authority.
- D4 `t_ae4b349e`: explicit refresh first, mandatory post-mutation readback, bounded recovery polling.
- Threat model `t_c5e9d4e4`: UI origin does not acquire extra authority.

## Critical concurrency correction

The D2 `board_revision` is UI-local. `adapter._read_ui_board_revision()` reads the `board_revision` table maintained by `UiMutationAdapter`; ordinary ChatGPT-side Hermes mutations do not reliably advance it. Therefore Interactive R1 MUST NOT use that value as a shared canonical freshness token.

The UI-local revision may remain for backwards-compatible D2 receipts, but it is not shared concurrency authority.

Until canonical CAS exists for metadata writes, actions that can silently overwrite user-authored fields are deferred.

## R1 allowlist

### Allowed now

| UI action | Canonical tool | Required scope | Concurrency property | Post-action proof |
| --- | --- | --- | --- | --- |
| Refresh board | `get_board` + `list_tasks` | read | read-only | new canonical snapshot |
| Inspect card | `get_task` | read | read-only | exact task readback |
| Create card | `create_task` | create | additive + idempotency key | created task `get_task` + board/list refresh |
| Add comment | `add_comment` | manage | append-only | task activity/readback contains comment/event |
| Assign card | `assign_task` | manage | explicit state mutation; actual canonical assignee wins | `get_task` assignee readback |
| Block card | `block_tasks` | manage | state-guarded | `get_task.status == blocked` or canonical skip/conflict shown |
| Unblock card | `unblock_tasks` | manage | state-guarded | fresh task/dispatch readback |
| Request review | `request_review` | manage | state-guarded | task becomes review / canonical response |
| Request changes | `request_changes` | manage | state-guarded | canonical review state readback |
| Reopen review | `reopen_review` | manage | state-guarded | canonical task state readback |

### Deferred until shared CAS/authority contract exists

- Edit title/body/priority (`update_task`): can overwrite a concurrent ChatGPT/human edit without an expected-task revision/fingerprint.
- Bulk reassign: same lost-update risk and broader blast radius.
- Schedule: defer to a later explicit workflow semantics review.
- Complete/archive: terminal or lifecycle-significant; separate R2 contract.
- Link/unlink DAG edges: graph integrity surface; separate R2 contract.

### Forbidden in this UI generation

- Human Gate approve/deny/decide.
- delete / hard archive removal / attachment removal.
- `gc`, `repair`, `swarm`.
- OAuth/DCR/token operations.
- service restart/deploy/traffic/routing.
- protected Git operations.

## Host bridge and authority

1. The UI sends `tools/call` through the existing host bridge.
2. Tool auth/scope remains authoritative. The UI never forges capability state.
3. The UI may use `get_board.capabilities` only for rendering controls; server-side scope enforcement is binding.
4. Board is always explicit in every mutation payload after initial selection.
5. Tenant is preserved from the selected task/create form where applicable; no hidden tenant switching.
6. UI provenance is presentation metadata only. It cannot elevate scope.

## Interaction lifecycle

Every mutation follows this state machine:

`CANONICAL_PRE_READ -> USER_CONFIRM -> TOOL_CALL -> TOOL_RESULT -> CANONICAL_POST_READ -> RECONCILED`

Failure states:

- Tool policy/auth rejection: show exact normalized error; do not mutate local state.
- Host error/timeout: show `UNKNOWN_OUTCOME`, force canonical readback before another mutation of the same card.
- Post-readback mismatch: show `RECONCILIATION_REQUIRED`; never show optimistic success.
- State guard conflict/skip: render canonical state and reason.

The card UI MUST disable duplicate submissions while one mutation is in flight.

## Idempotency

- `create_task`: generate one UUID idempotency key when the user submits; reuse the same key on explicit retry of the same request. A changed payload requires a new key.
- append/state tools without idempotency input: after any uncertain host outcome, perform canonical readback before allowing retry. Do not blind-retry.
- Never auto-retry a mutation solely because the iframe did not receive a timely response.

## Shared reconciliation: human and ChatGPT

### Explicit refresh

`Refresh` always performs `get_board` + `list_tasks`; selected card additionally performs `get_task`.

### Bounded live-sync burst

Interactive R1 MAY expose `Live sync (60s)` as an opt-in button:

- max 20 refresh cycles;
- minimum 3 seconds between cycles;
- only while document is visible;
- one in-flight refresh at a time;
- automatically stops after 60 seconds or when the resource is hidden/unloaded;
- user can stop early.

This is specifically how a ChatGPT-side mutation can become visible without inventing a permanent polling daemon or local event bus. No unbounded polling is permitted.

### Own-action reconciliation

After each UI mutation, perform immediate task + board/list readback. If the canonical effect is not yet visible, use D4-style bounded recovery polling only for that action (250ms, 500ms, 1s, 2s, 4s; max 5 attempts).

## UI controls

Board header:

- board picker;
- Refresh;
- Live sync (60s) / Stop;
- Create card.

Card row / inspector:

- Inspect;
- Comment;
- Assign;
- Block or Unblock based on canonical status;
- Review transition controls only when canonical current state makes them valid.

Controls unavailable by scope or state are disabled, not hidden when showing them helps explain why an action cannot be taken.

Human Gate cards display the existing exact-card readback/handoff surface only.

## Error and stale-state presentation

The UI maintains no optimistic shadow copy of task status/assignee. It may show a temporary `action in flight` indicator only.

On any mismatch between expected effect and canonical readback, canonical data replaces local display and the UI shows a conflict banner.

The legacy D2 UI-local `board_revision` MUST NOT label a board as fresh relative to ChatGPT-side mutations.

## Tests required for implementation

1. User create -> canonical readback -> UI shows task.
2. User comment -> canonical activity/readback contains comment.
3. User assign -> canonical assignee readback.
4. User block/unblock -> canonical state readback and expected guard behavior.
5. Review transition happy paths and invalid-state rejects.
6. ChatGPT/external fixture mutation between UI refreshes -> next Refresh replaces stale display.
7. ChatGPT/external mutation during Live sync burst -> visible within polling budget.
8. Unknown-outcome mutation -> no blind retry; canonical readback required.
9. Wrong board/tenant and insufficient scope -> fail closed.
10. Human Gate controls never include approve/deny/decide.
11. Forbidden tool names absent from the interactive resource script.
12. Bounded polling terminates at budget and on document hidden/unload.
13. No live fixtures remain after E2E.
14. Existing V1/read-only resource remains compatible.
15. Existing c257 gate/provenance behavior unchanged.

## Release boundary

Implementation is an isolated candidate only. A `PASS_FOR_INTERACTIVE_CANARY` review is required before any canary materialization/activation. That later activation must be exact-SHA bound and may not reuse an older Human Gate.
