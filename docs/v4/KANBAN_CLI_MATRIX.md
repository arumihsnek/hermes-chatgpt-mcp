# Hermes Kanban CLI Capability Matrix

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)
**Derived from:** t_4ce4ba8f (`HERMES-KANBAN-CLI-MATRIX-DRAFT.md`)
**Critical caveat:** CLI registration != behavioral PASS. The final catalog governs MCP status.

---

## Product Status Vocabulary (with emoji mapping for future use)## Product Status Vocabulary (with emoji mapping for future use)## Product Status Vocabulary (with emoji mapping for future use)

| Code | Emoji | Meaning |
|------|-------|---------|
| DISPONIBLE Y VALIDADO | ✅ | Registered in CLI, exercised via safe read call or board evidence, behavior confirmed |
| DISPONIBLE CON ERRORES/INCONSISTENCIAS | ⚠️ | Registered but known defect/inconsistency documented |
| EN TRABAJO | 🔧 | Actively being implemented in current development cycle |
| PLANIFICADO V4 | 🗓️ | Designed for V4 release, not yet implemented |
| PLANIFICADO V4.x | 🗓️+ | Designed for post-V4 minor release |
| PLANIFICADO V5 | 🗓️2 | Designed for next major version |
| NO DISPONIBLE/NO PLANIFICADO | ❌ | Not present, no active plan |
| NOT_PROVEN | ❓ | Registered/exists but behavior not exercised; only registration evidence |
| UNSAFE_TO_TEST | 🔒 | Would mutate production state (terminate, slash invocation, live kill) |
| NO APLICA AL MCP | N/A | Not relevant to MCP connector surface |

## Priority Codes

| Code | Meaning |
|------|---------|
| P0 | Blocking for V4 release |
| P1 | Important for V4, non-blocking |
| P2 | Nice to have for V4 |
| P3 | Deferred |
| DO_NOT_EXPOSE | Must not be exposed via MCP/connector |

---

## MCP Tool Name Mapping Convention

This matrix distinguishes three separate concepts per row:
- **CLI command**: The `hermes kanban <subcommand>` registered in CLI parser
- **Current Live MCP tool**: The exact tool name currently exposed by the live ChatGPT MCP connector (if any)
- **Planned V4 MCP tool**: The proposed tool name for V4 release (if applicable)

Do NOT derive MCP tool names by convention from CLI names. Only list names where explicit evidence exists.

---

## Matrix: Every `hermes kanban` Subcommand (47 registered)

### Global CLI Flag
| CLI Flag | Description | Status | Evidence |
|----------|-------------|--------|----------|
| `hermes kanban --board <slug>` | Global board selector for all subcommands | ✅ DISPONIBLE Y VALIDADO | t_59a2a2f5 |

### Subcommands

| # | CLI Command | Description | Flags/Semantics | Utility | Risk | Underlying Primitive | Current Live MCP Tool | Planned V4 MCP Tool | Validation Status | Known Issues | Priority | Target | Evidence |
|---|-------------|-------------|-----------------|---------|------|---------------------|----------------------|---------------------|-------------------|--------------|----------|--------|----------|
| 1 | `init` | Initialize new Kanban board | `--board <slug>` | Create board DB, schema, metadata | LOW | `kanban_db.init_db()` | N/A | N/A (admin) | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 2 | `boards` | List all boards | `--json` | Discovery, multi-board ops | LOW | `kanban_db.list_boards()` | N/A | `kanban_boards` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5, t_ef94f514 |
| 3 | `create` | Create new task | `--board`, `--assignee`, `--priority`, `--skills`, `--model`, `--provider`, `--reasoning`, `--workspace-kind`, `--workspace-path`, `--project`, `--triage`, `--idempotency-key`, `--max-runtime-seconds`, `--initial-status`, `--goal-mode`, `--goal-max-turns` | Task creation entry point | MEDIUM | `kanban_db.create_task()` | ✅ VALIDATED via MCP E2E | `kanban_create` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED | — | P0 | V4 | CLI: t_59a2a2f5; MCP: board QA evidence |
| 4 | `swarm` | Create multiple tasks | `--board`, `--parent`, `--count`, `--assignee` | Orchestrator fan-out | MEDIUM | `kanban_db.swarm_create()` | N/A | `kanban_swarm` | NOT_PROVEN | Not exercised | P1 | V4 | t_59a2a2f5 |
| 5 | `list` / `ls` | List tasks with filters | `--status`, `--assignee`, `--board`, `--json`, `--limit`, `--offset`, `--parent`, `--tags`, `--priority` | Primary read surface | LOW | `kanban_db.list_tasks()` | ✅ VALIDATED via MCP E2E | `kanban_list` | CLI leaf: ✅ VALIDATED; MCP E2E: ✅ VALIDATED | `ls` is alias for `list` | P0 | V4 | t_59a2a2f5, t_ad6925aa; MCP: board QA |
| 6 | `show` | Show full task state | `--board`, `--json` | Task inspection | LOW | `kanban_db.get_task()` | ✅ VALIDATED via MCP E2E | `kanban_show` | CLI leaf: ✅ VALIDATED; MCP E2E: ✅ VALIDATED | — | P0 | V4 | t_59a2a2f5, t_ad6925aa; MCP: board QA |
| 7 | `assign` | Assign task to profile | `--board`, `<task_id>`, `<assignee>` | Manual routing | MEDIUM | `kanban_db.assign_task()` | ✅ VALIDATED via MCP E2E | `kanban_assign` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED | — | P1 | V4 | CLI: t_59a2a2f5; MCP: board QA evidence |
| 8 | `set-model` | Override model/provider | `--board`, `<task_id>`, `--model`, `--provider`, `--reasoning` | Model pinning | MEDIUM | `kanban_db.set_task_model()` | N/A | `kanban_set-model` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 9 | `reclaim` | Reclaim stuck/running task | `--board`, `<task_id>`, `--force` | Stale task recovery | HIGH | `kanban_db.reclaim_task()` | N/A | `kanban_reclaim` | NOT_PROVEN | Destructive | P0 | V4 | t_59a2a2f5, t_ad6925aa |
| 10 | `reassign` | Reassign to different profile | `--board`, `<task_id>`, `<assignee>` | Routing correction | MEDIUM | `kanban_db.reassign_task()` | N/A | `kanban_reassign` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 11 | `diagnostics` / `diag` | Board health diagnostics | `--board`, `--json` | Observability | LOW | `kanban_db.diagnostics()` | N/A | `kanban_diagnostics` | CLI leaf: ✅ VALIDATED | `diag` is alias | P1 | V4 | t_59a2a2f5, t_ad6925aa |
| 12 | `link` | Add parent→child dependency | `--board`, `<parent_id>`, `<child_id>` | DAG construction | MEDIUM | `kanban_db.link_tasks()` | ✅ VALIDATED via MCP E2E | `kanban_link` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED | — | P1 | V4 | CLI: t_59a2a2f5; MCP: board QA evidence |
| 13 | `unlink` | Remove dependency edge | `--board`, `<parent_id>`, `<child_id>` | DAG repair | MEDIUM | `kanban_db.unlink_tasks()` | ✅ VALIDATED via MCP E2E | `kanban_unlink` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED | — | P2 | V4 | CLI: t_59a2a2f5; MCP: board QA evidence |
| 14 | `claim` | Claim task for worker | `--board`, `<task_id>` | Worker self-claim | MEDIUM | `kanban_db.claim_task()` | ✅ VALIDATED via MCP E2E | `kanban_claim` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED | Worker-only | P1 | V4 | CLI: t_59a2a2f5; MCP: board QA evidence |
| 15 | `comment` | Add comment to task | `--board`, `<task_id>`, `<body>` | Collaboration | LOW | `kanban_db.add_comment()` | ✅ VALIDATED via MCP E2E | `kanban_comment` | CLI leaf: ✅ VALIDATED; MCP E2E: ✅ VALIDATED | — | P1 | V4 | t_59a2a2f5; MCP: board QA evidence |
| 16 | `attach` | Attach file (base64 inline) | `--board`, `<task_id>`, `--content-base64`, `--filename`, `--content-type` | File upload | MEDIUM | `kanban_db.store_attachment_bytes()` | ⚠️ PARTIAL: `local_path` only; no `content_base64` | `kanban_attach` | CLI leaf: ✅ VALIDATED (agent tool); MCP E2E: ⚠️ STAGING_BOUND (local_path only) | MCP connector lacks `content_base64`; SERVER_LOCAL_BOUND | P0 | V4 | t_59a2a2f5, t_2499ad0a; MCP: CONFLICT evidence |
| 17 | `attachments` | List task attachments | `--board`, `<task_id>`, `--json` | File listing | LOW | `kanban_db.list_attachments()` | N/A | `kanban_attachments` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 18 | `attach-rm` | Remove attachment | `--board`, `<task_id>`, `<attachment_id>` | Cleanup | MEDIUM | `kanban_db.remove_attachment()` | N/A | `kanban_attach-rm` | NOT_PROVEN | — | P2 | V4 | t_59a2a2f5 |
| 19 | `complete` | Complete task with handoff | `--board`, `<task_id>`, `--summary`, `--metadata`, `--result`, `--artifacts`, `--created-cards` | Task termination | HIGH | `kanban_db.complete_task()` | ✅ VALIDATED via MCP E2E | `kanban_complete` | CLI leaf: ✅ VALIDATED; MCP E2E: ✅ VALIDATED | — | P0 | V4 | t_59a2a2f5; MCP: board QA evidence |
| 20 | `edit` | Edit task fields | `--board`, `<task_id>`, `--title`, `--body`, `--priority`, `--assignee` | Task mutation | MEDIUM | `kanban_db.edit_task()` | N/A | `kanban_edit` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 21 | `block` | Block task with reason/kind | `--board`, `<task_id>`, `--reason`, `--kind` | Explicit block | MEDIUM | `kanban_db.block_task()` | ✅ VALIDATED via MCP E2E | `kanban_block` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED | — | P1 | V4 | CLI: t_59a2a2f5; MCP: board QA evidence |
| 22 | `schedule` | Schedule future task | `--board`, `--at`, `--cron`, `--title`, `--body` | Deferred work | MEDIUM | `kanban_db.schedule_task()` | N/A | `kanban_schedule` | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 23 | `unblock` | Unblock task | `--board`, `<task_id>` | Resume blocked | MEDIUM | `kanban_db.unblock_task()` | N/A | `kanban_unblock` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 24 | `request-review` | Move to review column | `--board`, `<task_id>`, `--summary`, `--reviewer`, `--metadata` | Review gate | MEDIUM | `kanban_db.request_review()` | N/A | `kanban_request-review` | NOT_PROVEN | Force-loads sdlc-review | P0 | V4 | t_59a2a2f5, t_2d78d03f |
| 25 | `request-changes` | Return review to implementer | `--board`, `<task_id>`, `--reason` | Review rejection | MEDIUM | `kanban_db.request_changes()` | N/A | `kanban_request-changes` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 26 | `reopen-review` | Reopen closed review | `--board`, `<task_id>` | Review cycle | MEDIUM | `kanban_db.reopen_review()` | N/A | `kanban_reopen-review` | NOT_PROVEN | — | P2 | V4 | t_59a2a2f5 |
| 27 | `promote` | Promote ready children | `--board`, `<task_id>` | DAG promotion | MEDIUM | `kanban_db.promote_children()` | N/A | `kanban_promote` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 28 | `archive` | Archive completed task | `--board`, `<task_id>` | Cleanup | MEDIUM | `kanban_db.archive_task()` | N/A | `kanban_archive` | NOT_PROVEN | — | P2 | V4 | t_59a2a2f5 |
| 29 | `tail` | Tail task log | `--board`, `<task_id>`, `--lines`, `--follow` | Live logs | LOW | `kanban_db.tail_log()` | N/A | `kanban_tail` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 30 | `dispatch` | Single dispatch tick | `--board`, `--once` | Manual dispatch | HIGH | `kanban_db.dispatch_once()` | N/A | `kanban_dispatch` | NOT_PROVEN | Embedded in gateway | P1 | V4 | t_59a2a2f5, t_ad6925aa |
| 31 | `daemon` | Standalone dispatch daemon | `--interval`, `--max`, `--failure-limit`, `--pidfile`, `--verbose` | Legacy dispatch | HIGH | `kanban_db.run_daemon()` | N/A | N/A | ⚠️ DEPRECATED | Marked DEPRECATED; use `hermes gateway start` | DO_NOT_EXPOSE | NO APLICA | t_59a2a2f5, t_ad6925aa |
| 32 | `watch` | Watch board for changes | `--board`, `--interval` | Live monitoring | LOW | `kanban_db.watch()` | N/A | `kanban_watch` | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 33 | `stats` | Board statistics | `--board`, `--json` | Metrics | LOW | `kanban_db.stats()` | N/A | `kanban_stats` | CLI leaf: ✅ VALIDATED | — | P1 | V4 | t_59a2a2f5, t_ef94f514 |
| 34 | `notify-subscribe` | Subscribe to notifications | `--board`, `--channel`, `--filter` | Event streaming | LOW | `kanban_db.subscribe()` | N/A | `kanban_notify-subscribe` | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 35 | `notify-list` | List subscriptions | `--board`, `--json` | Subscription mgmt | LOW | `kanban_db.list_subscriptions()` | N/A | `kanban_notify-list` | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 36 | `notify-unsubscribe` | Remove subscription | `--board`, `<subscription_id>` | Cleanup | LOW | `kanban_db.unsubscribe()` | N/A | `kanban_notify-unsubscribe` | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 37 | `log` | Task event log | `--board`, `<task_id>`, `--tail`, `--json` | History | LOW | `kanban_db.get_log()` | N/A | `kanban_log` | CLI leaf: ✅ VALIDATED | — | P1 | V4 | t_59a2a2f5, t_ad6925aa |
| 38 | `runs` | Task run history | `--board`, `<task_id>`, `--json` | Attempt history | LOW | `kanban_db.get_runs()` | N/A | `kanban_runs` | CLI leaf: ✅ VALIDATED | — | P0 | V4 | t_59a2a2f5, t_ad6925aa |
| 39 | `heartbeat` | Send worker heartbeat | `--board`, `<task_id>`, `--note` | Liveness | LOW | `kanban_db.heartbeat_claim()` | N/A | `kanban_heartbeat` | CLI leaf: ❓ NOT_PROVEN; MCP E2E: ✅ VALIDATED (tool exists) | Worker-only | P1 | V4 | t_59a2a2f5; MCP: tool registered |
| 40 | `assignees` | List dispatcher-eligible profiles | `--board`, `--json` | Profile discovery | LOW | `kanban_db.list_assignees()` | N/A | `kanban_assignees` | CLI leaf: ✅ VALIDATED | — | P0 | V4 | t_59a2a2f5, t_c2257b50 |
| 41 | `context` | Get task context for worker | `--board`, `<task_id>`, `--json` | Worker bootstrap | LOW | `kanban_db.get_context()` | N/A | `kanban_context` | CLI leaf: ✅ VALIDATED | — | P1 | V4 | t_59a2a2f5 |
| 42 | `specify` | Add acceptance criteria | `--board`, `<task_id>`, `--criteria` | AC tracking | MEDIUM | `kanban_db.specify()` | N/A | `kanban_specify` | NOT_PROVEN | — | P2 | V4.x | t_59a2a2f5 |
| 43 | `decompose` | Auto-decompose triage task | `--board`, `<task_id>` | Orchestrator | MEDIUM | `kanban_db.decompose_task()` | N/A | `kanban_decompose` | NOT_PROVEN | — | P1 | V4 | t_59a2a2f5 |
| 44 | `gc` | Garbage collect old data | `--board`, `--days` | Maintenance | HIGH | `kanban_db.gc()` | N/A | `kanban_gc` | NOT_PROVEN | Destructive | P2 | V4.x | t_59a2a2f5 |
| 45 | `repair` | Repair board inconsistencies | `--board` | Recovery | HIGH | `kanban_db.repair()` | N/A | `kanban_repair` | NOT_PROVEN | Destructive | P1 | V4 | t_59a2a2f5 |
| 46 | `ls` | Alias for `list` | Same flags as `list` | Primary read surface alias | LOW | Alias → `kanban_db.list_tasks()` | ✅ VALIDATED via MCP E2E | `kanban_list` | CLI alias: ✅ VALIDATED by parser; MCP E2E follows `list_tasks` | Alias; see row 5 | P0 | V4 | t_59a2a2f5 |
| 47 | `diag` | Alias for `diagnostics` | Same flags as `diagnostics` | Observability alias | LOW | Alias → `kanban_db.diagnostics()` | N/A | `kanban_diagnostics` | CLI alias: ✅ VALIDATED by parser; behavior follows `diagnostics` | Alias; see row 11 | P1 | V4 | t_59a2a2f5 |

---

## Validation Legend

| Symbol | Meaning |
|--------|---------|
| CLI leaf: ✅ VALIDATED | Safe read call or prior board evidence confirms behavior |
| CLI leaf: ❓ NOT_PROVEN | Only `--help` registration evidence; leaf behavior not exercised |
| MCP E2E: ✅ VALIDATED | Tested via MCP tool call on this board (assign, comment, link, etc.) |
| MCP E2E: ⚠️ PARTIAL | MCP tool exists but has known limitation (e.g., local_path-only attach) |
| N/A | No MCP equivalent exists or is planned |

---

## Special Notes

### Aliases
| Alias | Target | Status |
|-------|--------|--------|
| `ls` | `list` | ALIAS |
| `diag` | `diagnostics` | ALIAS |

### Deprecated
| Command | Replacement | Status |
|---------|-------------|--------|
| `daemon` | `hermes gateway start` (embedded dispatcher) | ⚠️ DEPRECATED → DO_NOT_EXPOSE / NO APLICA AL MCP |

### Absent from CLI (confirmed)
| Missing Command | Notes |
|-----------------|-------|
| `pause` / `resume` (board-local) | Only global `hermes pause`/`resume` exists (ESTOP sentinel) |
| `workers` | Worker visibility via `runs`, `diagnostics`, dashboard API only |

---

## Critical Caveats

1. **Registration ≠ Operational PASS**: `--help` registration proves the command exists in the CLI parser. It does NOT prove operational PASS for every leaf subcommand. Actual leaf behavior is only proven where a real safe read call, prior board evidence, or MCP E2E test exists. Commands like `dispatch`, `watch`, `schedule`, `swarm`, `repair`, `gc` are registered but leaf behavior is unverified beyond source inspection.

2. **MCP Connector Gap**: The current live MCP connector exposes `attach(local_path=...)` only — it is SERVER_LOCAL/STAGING_BOUND (requires file on server filesystem within `MCP_ATTACHMENT_STAGING_ROOT`). Remote clients cannot provide server-local paths. V4 must add `content_base64` field to MCP connector's AttachInput schema. (Evidence: t_2499ad0a)

3. **Size Cap Mismatch**: Agent tool `KANBAN_ATTACHMENT_MAX_BYTES = 25 MB`; MCP connector default `MCP_MAX_ATTACHMENT_BYTES = 10 MB`. Must unify. (Evidence: t_2499ad0a)

4. **Deployed Connector SHA Unknown**: Local master fd0286c lacks attach tool; beta/worktree 9900c10 has it; live schema confirms deployed version is ahead. Exact deployed SHA is STILL_NOT_PROVEN. (Evidence: t_2499ad0a)

5. **sdlc-review Force-Load**: `request-review` force-loads `sdlc-review` into review workers at dispatch time (`kanban_db.py:10384`). This is production-critical and must be preserved. (Evidence: t_2d78d03f)

6. **MCP E2E Evidence Reuse**: Prior QA on this board validated assign, comment, link, unlink, claim, heartbeat, transitions, and notifications via MCP tool calls. These are marked MCP E2E: ✅ VALIDATED even where the local CLI leaf behavior was not independently re-run. CLI and MCP validation status are tracked independently.

---

## P0/P1 Summary for V4

| Priority | CLI Commands |
|----------|-------------|
| **P0** | `create`, `complete`, `reclaim`, `request-review` (force-load), `attach` (base64 gap), `list`, `show`, `runs`, `assignees` |
| **P1** | `boards`, `assign`, `set-model`, `reassign`, `diagnostics`, `link`, `comment`, `edit`, `block`, `unblock`, `request-changes`, `promote`, `tail`, `stats`, `log`, `heartbeat`, `context`, `dispatch`, `repair` |
| **P2** | `init`, `swarm`, `schedule`, `attach-rm`, `unlink`, `attachments`, `archive`, `watch`, `notify-*`, `specify`, `decompose`, `gc` |
| **DO_NOT_EXPOSE / NO APLICA** | `daemon` (deprecated) |

---

## Evidence Traceability

| Evidence Source | Task | Artifacts |
|-----------------|------|-----------|
| CLI enumeration | t_59a2a2f5 | `findings.txt` (attached), completion metadata |
| Synthesis ledger | t_2d568471 | `V4-LOCAL-SYNTHESIS-REPORT_1.md`, `synthesis-metadata.json` |
| Runtime investigation | t_ad6925aa | `V4-LOCAL-RUNTIME-report.md` |
| Config investigation | t_ef94f514 | `V4-LOCAL-CONFIG-report.md` |
| Attachments contract | t_2499ad0a | `REPORT-t_2499ad0a-attachments-contract.md` |
| Skills investigation | t_2d78d03f | `V4-LOCAL-SKILLS-INVESTIGATION_1.md` |
| Profiles investigation | t_c2257b50 | `V4-LOCAL-PROFILES-INVESTIGATION.md` |
| Native tools inventory | t_5caf4595 | `native_tools_inventory.json`, `native_tools_inventory_report.md` |
| MCP E2E QA | Prior board QA evidence | Board event history (assign, comment, link, unlink, claim, heartbeat, transitions validated) |