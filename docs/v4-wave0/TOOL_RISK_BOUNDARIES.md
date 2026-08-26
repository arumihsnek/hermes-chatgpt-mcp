# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef + d7eba25
# Candidate: wt/t_261a7674 — Wave 0 tool risk/scope boundaries

Status: see docs/v4-wave0/ADR-001-foundation.md
Version: v4.wave0

## Scope model

| Scope | Boards | Grants | Tools |
|-------|--------|--------|-------|
| hermes:read | global (all active canonical named boards) | no board claim | 7 reads: list_boards/get_board/list_tasks/get_task/get_task_graph/get_dispatch/get_activity |
| hermes:create | one-board | board + board_access=write | create_task |
| hermes:manage | one-board | board + board_access=write | add_comment/assign_task (+ full lifecycle in full V4) |
| hermes:board:create | global | no board claim | create_board (does NOT grant task write) |
| hermes:admin | global | no board claim (beta: board claim forbidden) | sensitive leaves (init/swarm/dispatch/daemon/gc/repair/boards-rm/…) |
| offline_access | — | — | refresh only |

## Annotations (MCP ToolAnnotations)

- READ: readOnlyHint=true, destructiveHint=false, idempotentHint=true, openWorldHint=false
- create_*: readOnlyHint=false, destructiveHint=false, idempotentHint=true
- manage: readOnlyHint=false, destructiveHint=false, idempotentHint=false
- admin: readOnlyHint=false (varies), guarded by hermes:admin

ChatGPT compat mode freezes to 11 tools (7 reads + create_task/create_board/add_comment/assign_task) on beta only.

## Fail-closed rules

- Scope missing → SCOPE_REQUIRED
- Command scope without board claim → BOARD_WRITE_SELECTION_REQUIRED
- Board mismatch vs grant → BOARD_SESSION_MISMATCH (no fallback to default)
- Unknown board → BOARD_NOT_FOUND (no existence leak)
- Unknown task → TASK_NOT_FOUND
- Schema extra fields → 422 (extra=forbid) before handler runs
- Invalid provenance/manifest → BuildMetadataError → 500 at startup, never silent

## Backwards compatibility

Additive headers only: X-V4-Provenance, X-API-Version, X-Baseline-Branch, X-Baseline-MCP.
Stable /healthz body unchanged ({status:ok}); beta body adds {build:{build_commit,surface,deployed_at}}.
Rollback: revert wt/t_261a7674 commits; headers disappear, stable reverts to prior.
