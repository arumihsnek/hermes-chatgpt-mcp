# Hermes ChatGPT MCP V4 Dogfood / QA Plan

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19 (canonical design) + **2026-08-21 release-candidate truth-sync** (see [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md))
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)
**Derived from:** t_8a7b081c (`V4-DOGFOOD-QA-PLAN-DRAFT.md`)

---

## Phase-S Candidate E2E — Fresh-Session / Provenance Handshake (2026-08-21 truth-sync — supplemental)

This section adds the immediate Phase-S candidate E2E bridge on top of the V4 dogfood plan. It is **not** a replacement for the disposable-fixture rule below; it tightens the canary entry condition. See [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md) §6 and task `t_be036abf` (comment 580).

**Entry gate before the canary's first mutation:**
1. Establish a **fresh MCP/OAuth session** — no token/session reused from prior QA.
2. Capture a **minimal observed receipt**:
   - expected canary / release ID
   - Connector SHA
   - Core SHA / version
   - schema / tool-surface version
   - scopes **actually granted / effective** (not merely requested)
3. **Mismatch or unknown identity ⇒ FAIL before any mutation.** Do not proceed; do not write to the live board.

**Coverage vs architecture:** This handshake provides *immediate-E2E* coverage for G2 / G6 / G14 / G15 / G16 (identity/scope readback). It is **not** a substitute for their full identity/session architecture, which remains later Wave0+ / other layers.

> A provenance `GO` (e.g. `t_dadd5ebf`) is evidence, **not** release/build/deploy authorization. This handshake is a prerequisite gate, not the exact-release human gate.

## Overview## Overview
This plan uses the Hermes ChatGPT MCP connector itself as both subject and control plane for dogfooding and QA. All tests and validation will be performed using the MCP interface. CLI/source may appear only in an `Oracle/contrast` column or note for verification.

## Scope
Cover discovery/readback, create/edit/assign, profile/skill validation, workers/runs, attachments, events/notifications, negative schemas, boundedness, idempotency, authorization, admin guards, build provenance, stale connector discovery, and regression fixtures.

**Do not execute QA fixtures now** - this is a plan only. Execution will happen in subsequent work.

## Test Environment
- Workspace: `$HERMES_KANBAN_WORKSPACE` (scratch)
- Profile: operator (for execution)
- Board: `hermes-chatgpt-e2e-*` disposable fixture board(s) for ALL mutating QA. NEVER use project board `hermes-chatgpt-mcp` for mutations. Read-only control-plane checks may read the project board if needed.
- Connector: Hermes ChatGPT MCP (subject under test)

## Current MCP Tool Surface (LIVE CONNECTOR DISCOVERY — authoritative)
**CURRENT read/introspection tools exposed by live discovery (18 listed):**
`list_boards`, `get_board`, `list_tasks`, `get_task`, `get_task_graph`, `get_dispatch`, `get_activity`, `diagnostics`, `attachments`, `stats`, `log`, `runs` (task-scoped), `assignees`, `context`, `tail`, `watch`, `daemon` (status/snapshot only), `notify-list`

**CURRENT writes/actions exposed by live discovery (separate from reads):**
`create_task`, `create_board`, `add_comment`, `assign_task`, `link_tasks`, `unlink_tasks`, `set_model`, `reclaim_task`, `reassign_tasks`, `complete_tasks`, `edit_task` (COMPLETED TASK RESULT only), `block_tasks`, `schedule_tasks`, `unblock_tasks`, `request_review`, `request_changes`, `reopen_review`, `promote_tasks`, `archive_tasks`, `claim`, `attach` (local_path only), `attach-rm`, `heartbeat`, `specify`, `init`, `swarm`, `dispatch`, `decompose`, `gc`, `repair`, `notify-subscribe`, `notify-unsubscribe`, `boards-rm`, `boards-switch`, `boards-rename`, `boards-set-default-workdir`

`CURRENT` means exposed by live connector discovery; behavioral status/validation is a separate test outcome. The full live surface is 54 tools across reads and writes; the lists above enumerate the authoritative current read and write groups relevant to this plan.

**Key distinctions from LIVE discovery:**
- `stats` not `get_stats`
- `runs` (task-scoped) not `get_runs`/`get_run`
- `assignees` not `list_profiles`/`get_assignees`/`get_profile`
- `list_profiles` is PLANNED V4 rich contract
- `get_dispatch` is CURRENT dispatch eligibility read, NOT substitute for `runs`
- `runs(task_id)` itself is CURRENT
- `attach(local_path)` CURRENT but `attach(content_base64)` remote PLANNED V4 extension
- Full general `edit_task` contract PLANNED V4 despite current result-only `edit_task`
- `get_runtime_info`/`list_skills`/`get_skill`/profile validation PLANNED V4
- `dispatch` CURRENT but known `BACKEND_ERROR` observed in manual call => mark current/inconsistent
- `daemon` CURRENT bounded status/snapshot even though standalone CLI daemon deprecated
- `gc`, `repair`, `boards-rm`, workdir mutation CURRENT but high-risk/admin/DO_NOT_EXPOSE-normal-use
- CLI negative oracle `hermes skills inspect` must stay outside MCP-call column

## Test Categories

### 1. Discovery & Readback
| MCP Call Under Test | Status | Oracle/Contrast (CLI/Source) |
|---------------------|--------|------------------------------|
| `get_board` | CURRENT | `hermes kanban show <task_id>` / `hermes kanban boards` |
| `list_tasks` | CURRENT | `hermes kanban list` with filters |
| `get_task` | CURRENT | `hermes kanban show <task_id>` |
| `get_activity` | CURRENT | `hermes kanban log` / event stream |
| `get_task_graph` | CURRENT | `hermes kanban context` (task graph) |
| `get_dispatch` | CURRENT | `hermes kanban runs <task_id> --json` (dispatch eligibility) |
| `diagnostics` | CURRENT | `hermes kanban diagnostics` |
| `attachments` | CURRENT | `hermes kanban attachments` |
| `stats` | CURRENT | `hermes kanban stats` |
| `log` | CURRENT | `hermes kanban tail` / `hermes kanban log` |
| `runs` (task-scoped) | CURRENT | `hermes kanban runs <task_id> --json` |
| `assignees` | CURRENT | `hermes kanban assignees --json` |
| `context` | CURRENT | `hermes kanban context` |
| `tail` | CURRENT | `hermes kanban tail` |
| `watch` | CURRENT | `hermes kanban watch` |
| `daemon` (status/snapshot) | CURRENT | `hermes kanban daemon` |
| `notify-list` | CURRENT | `hermes kanban notify-list` |
| `list_profiles` | PLANNED V4 (richer) | `hermes profile list` |
| `get_version` | PLANNED V4 | `hermes version` (v0.20.2) |
| `list_skills` | PLANNED V4 | `hermes skills list` (53 enabled) |

### 2. Create/Edit/Assign (on disposable `hermes-chatgpt-e2e-*` fixture boards only)
| MCP Call Under Test | Status | Oracle/Contrast (CLI/Source) |
|---------------------|--------|------------------------------|
| `create_task` (title, body, parent_ids, assignee, priority, tenant, idempotency_key) | CURRENT | `hermes kanban create` |
| `create_board` | CURRENT | `hermes kanban boards` |
| `add_comment` | CURRENT | `hermes kanban comment` |
| `assign_task` | CURRENT | `hermes kanban assign` |
| `link_tasks` | CURRENT | `hermes kanban link` |
| `unlink_tasks` | CURRENT | `hermes kanban unlink` |
| `set_model` | CURRENT | `hermes kanban set-model` |
| `reclaim_task` | CURRENT | `hermes kanban reclaim` |
| `reassign_tasks` | CURRENT | `hermes kanban reassign` |
| `complete_tasks` | CURRENT | `hermes kanban complete` |
| `edit_task` (COMPLETED TASK RESULT only) | CURRENT | `hermes kanban edit` (result only) |
| `edit_task` (general task body) | PLANNED V4 | `hermes kanban edit` (body) |
| `block_tasks` | CURRENT | `hermes kanban block` |
| `schedule_tasks` | CURRENT | `hermes kanban schedule` |
| `unblock_tasks` | CURRENT | `hermes kanban unblock` |
| `request_review` | CURRENT | `hermes kanban request-review` |
| `request_changes` | CURRENT | `hermes kanban request-changes` |
| `reopen_review` | CURRENT | `hermes kanban reopen-review` |
| `promote_tasks` | CURRENT | `hermes kanban promote` |
| `archive_tasks` | CURRENT | `hermes kanban archive` |
| `claim` | CURRENT | `hermes kanban claim` |
| `specify` | CURRENT | `hermes kanban specify` |
| `init` | CURRENT | `hermes kanban init` |
| `swarm` | CURRENT | `hermes kanban swarm` |
| `dispatch` | CURRENT (inconsistent - BACKEND_ERROR observed) | `hermes kanban dispatch` |
| `decompose` | CURRENT | `hermes kanban decompose` |
| `boards-rm` | CURRENT (DO_NOT_EXPOSE-normal-use) | `hermes kanban boards-rm` |
| `boards-switch` | CURRENT | `hermes kanban boards-switch` |
| `boards-rename` | CURRENT | `hermes kanban boards-rename` |
| `boards-set-default-workdir` | CURRENT (DO_NOT_EXPOSE-normal-use) | `hermes kanban boards-set-default-workdir` |

### 3. Profile/Skill Validation
| MCP Call Under Test | Status | Oracle/Contrast (CLI/Source) |
|---------------------|--------|------------------------------|
| `validate_profile` (pre-assign) | PLANNED V4 | `hermes kanban assignees --json` shows `on_disk=true` |
| `get_skill` / skill validation (force-load sdlc-review) | PLANNED V4 | Source: `kanban_db.py:10384` force-load |
| Profile toolset calculation | PLANNED V4 | Compare MCP toolset vs runtime effective toolsets (not yaml) |
| `list_profiles` (richer) | PLANNED V4 | `hermes profile list` |
| `get_profile` | PLANNED V4 | Source: profile.yaml |

### 4. Workers/Runs/Inspect
| MCP Call Under Test | Status | Oracle/Contrast (CLI/Source) |
|---------------------|--------|------------------------------|
| Dispatch → verify worker spawn | PLANNED V4 | `hermes kanban list --status running` |
| `runs` (task_id) | CURRENT | `hermes kanban runs <task_id> --json` |
| `get_run` (run_id) | PLANNED V4 | Dashboard: `GET /api/plugins/kanban/runs/{run_id}` |
| `inspect_run` (run_id) | PLANNED V4 | Dashboard: `GET /api/plugins/kanban/runs/{run_id}/inspect` (psutil) |
| `workers_active` | PLANNED V4 | `hermes kanban list --status running` |
| Heartbeat events | PLANNED V4 | Task event stream / `heartbeat` |
| Worker env vars (HERMES_PROFILE, etc.) | PLANNED V4 | Source: `_default_spawn()` at `kanban_db.py:10709` |
| `complete_tasks` | CURRENT | `hermes kanban complete` → verify done column |
| Guarded terminate | PLANNED V4 | `POST /api/plugins/kanban/runs/{run_id}/terminate` → `reclaim_task()` |

### 5. Attachments (bytes/base64 and traversal/size/MIME)
| MCP Call Under Test | Status | Oracle/Contrast (CLI/Source) |
|---------------------|--------|------------------------------|
| `attach` (local_path) | CURRENT | `hermes kanban attach` local_path |
| `attach` (content_base64) | PLANNED V4 | `hermes kanban attach` base64 (agent has it; MCP transport missing) |
| Size rejection (>25MB) | PLANNED V4 | Verify unified 25MB policy enforcement |
| `attachments` | CURRENT | `hermes kanban attachments` |
| `attach-rm` | CURRENT | `hermes kanban attach-rm` |
| Round-trip integrity | PLANNED V4 | Verify content hash match |

### 6. Events/Notifications
| MCP Call Under Test | Status | Oracle/Contrast (CLI/Source) |
|---------------------|--------|------------------------------|
| `log` / `tail` / `watch` | CURRENT | Event stream / `hermes kanban log` |
| Task create → event stream | PLANNED V4 | Event stream |
| Task edit → update event | PLANNED V4 | Event stream |
| Task assign → assignment event | PLANNED V4 | Event stream |
| Task complete → completion event | PLANNED V4 | Event stream |
| Webhook delivery (if configured) | PLANNED V4 | Webhook endpoint logs |
| Notification content | PLANNED V4 | Verify relevant details present |
| Event ordering/consistency | PLANNED V4 | Sequence check |
| `notify-subscribe` | CURRENT | `hermes kanban notify-subscribe` |
| `notify-unsubscribe` | CURRENT | `hermes kanban notify-unsubscribe` |

### 7. Negative Schemas/Validation
| MCP Call Under Test (expected failure) | Status | Oracle/Contrast |
|----------------------------------------|--------|-----------------|
| `get_task` invalid task_id | CURRENT | Error code/message |
| `create_task` missing required fields | CURRENT | Error code/message |
| `create_task` invalid idempotency_key | CURRENT | Error code/message |
| `assign_task` invalid profile | CURRENT | Error code/message |
| `set_model` invalid model | CURRENT | Error code/message |
| `edit_task` invalid (non-result) edit | PLANNED V4 | Error code/message |
| Duplicate attachment names | CURRENT | Error code/message |
| Oversized attachment (>25MB) | PLANNED V4 | Error code/message |
| Invalid base64 in attach | PLANNED V4 | Error code/message |
| Invalid JSON in complex fields | PLANNED V4 | Error code/message |

### 8. Boundedness
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| Task depth limits | PLANNED V4 | System stability |
| Comment size limits | PLANNED V4 | Error/behavior at boundary |
| Attachment count limits per task | PLANNED V4 | Error/behavior at boundary |
| Title/body length limits | PLANNED V4 | Error/behavior at boundary |
| Idempotency key uniqueness | CURRENT | Enforcement |
| Rate limiting behavior | PLANNED V4 | Behavior under load |
| System stability at boundaries | PLANNED V4 | No crashes/corruption |

### 9. Idempotency
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| `create_task` same key → no duplicate | CURRENT | Verify same result |
| `add_comment` same key → no duplicate | PLANNED V4 | Verify same result |
| `link_tasks` same key → no duplicate | PLANNED V4 | Verify same result |
| Different keys → different resources | PLANNED V4 | Verify distinct |
| Key persistence across restarts | PLANNED V4 | Verify after restart |

### 10. Authorization/Admin Guards
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| Admin actions require auth | CURRENT (partial) | `hermes pause`/`resume` (global ESTOP) |
| Pause → stops dispatch | PLANNED V4 | `hermes kanban list --status ready` unchanged |
| Resume → restores dispatch | PLANNED V4 | Tasks picked up |
| `reclaim_task` (terminate) | CURRENT | `hermes kanban reclaim` |
| `dispatch` | CURRENT (inconsistent) | `hermes kanban dispatch` |
| Timeout reclamation | PLANNED V4 | Dispatch stale timeout (4h) reclaims |
| Failure limit (2 consecutive → block) | PLANNED V4 | Auto-block behavior |
| `gc` | CURRENT (DO_NOT_EXPOSE-normal-use) | `hermes kanban gc` |
| `repair` | CURRENT (DO_NOT_EXPOSE-normal-use) | `hermes kanban repair` |
| Admin permission enforcement | PLANNED V4 | Unauthorized fails |

### 11. Build Provenance
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| `get_runtime_info` | PLANNED V4 | `hermes version` (v0.20.2, upstream SHA, install source/method) |
| `diagnostics` (connector SHA) | CURRENT | `hermes kanban diagnostics` |
| Build timestamp | PLANNED V4 | `hermes version` output |
| Version consistency | PLANNED V4 | Repeated calls |

### 12. Stale Connector Discovery
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| Connector label discovery (`get_board` metadata) | CURRENT | `Kanban_Beta` recognized as stale |
| Backend stability evidence | CURRENT (controller) | Controller correction: deployment is STABLE |
| Label doesn't affect functionality | CURRENT | Functional parity |
| Documentation warning | PLANNED V4 | Docs warn against inferring beta from label |
| Version detection | PLANNED V4 | Correct version reported |

### 13. Current/Proposed V4 Capability Reporting
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| OAuth scopes/capability reporting (`get_board` capabilities) | CURRENT (partial - `capabilities.create` flag) | Current proven: `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create` (+ offline_access) |
| `get_board` capability readback inconsistency | CURRENT (known issue) | Known issue: readback inconsistent with successful writes |
| Embedded dispatcher vs manual dispatch | CURRENT (dispatch exists) | Source: `kanban.dispatch_in_gateway=true` |
| Registration != behavioral PASS | CURRENT (observed) | CLI `--help` registration vs actual PASS |

### 14. Regression Fixtures (Reference Only — Monitor for Regressions)
- LOCAL-001 through LOCAL-008 classifications
- Section 14 NOT_PROVEN items
- Section 13 Docs/runtime discrepancies
- Skill system limitations (inspect vs list/view)
- sdlc-review force-load mechanism
- Profile toolset/runtime mismatch
- MCP connector gaps (addressed in P0)
- Profile capabilities/refuses advisory nature
- **Fixture-board isolation guard** — dogfood MUST use disposable `hermes-chatgpt-e2e-*` fixtures; `t_a161305b`/run1114 and `t_85b5b14b`/run1118 leaked onto canonical board (`pid999999`/`boom`/`worker`), reclaimed+archived (no DELETE), review PASS. Root = `gave_up`+`promoted` without atomic run/claim closure + test isolation failure. Canonical record: [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md) §4.

### 15. Artifact-Completion Lifecycle Regression (from THIS docs program)
| MCP Call Under Test | Status | Oracle/Contrast |
|---------------------|--------|-----------------|
| `complete_tasks` freezes result/artifacts | CURRENT | Verify durable completion record |
| Later workspace edits → NO silent mutation | PLANNED V4 | Completed artifacts immutable |
| Corrections require explicit reissue/versioning | PLANNED V4 | New task/version for corrections |
| Observed lifecycle behavior codified | PLANNED V4 | Test passes as regression guard |

## Test Procedures
Each test should:
1. Set up any required preconditions on disposable `hermes-chatgpt-e2e-*` fixture board
2. Execute the test action via **MCP call** (subject under test)
3. Verify the expected outcome
4. Cross-reference with Oracle/Contrast (CLI/source) where noted
5. Check for side effects (events, state changes)
6. Clean up test artifacts if appropriate
7. Record pass/fail with evidence

## Evidence Collection
For each test, collect:
- MCP call executed (method + params)
- Full MCP response
- Exit/status code
- Before/after state snapshots (if applicable)
- Event stream changes
- Performance metrics (if relevant)
- Oracle/Contrast CLI output for verification

## Success Criteria
- All CURRENT discovery/readback/write MCP calls pass
- All PLANNED V4 profile/skill validation MCP calls pass
- All PLANNED V4 workers/runs/inspect MCP calls pass
- All PLANNED V4 attachment MCP calls pass (including edge cases)
- All PLANNED V4 events/notifications MCP calls pass
- All negative schema MCP calls fail appropriately with correct errors
- All boundedness MCP calls pass or fail gracefully
- All idempotency MCP calls pass
- All authorization/admin guard MCP calls pass
- All build provenance MCP calls pass
- All stale connector discovery MCP calls pass
- Capability reporting MCP calls cover current/proposed V4 items
- Artifact-completion lifecycle regression MCP test present and passing
- No unexplained regressions in LOCAL-001..008

## Exit Criteria
Dogfood/QA plan is considered complete when:
- All test procedures are documented with MCP calls as subject
- Evidence collection methods defined
- Success criteria established
- Ready for execution in subsequent work
- All mutating tests explicitly use disposable `hermes-chatgpt-e2e-*` fixture boards
- No test step has `hermes kanban` as the primary action under test (CLI only as oracle)