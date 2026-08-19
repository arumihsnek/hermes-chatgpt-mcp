# V4 Current State — Canonical Source of Truth

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)

---

## 1. Evidence Provenance Hierarchy

This document derives exclusively from **local read-only investigations** completed on 2026-08-19. No public research, no repository modifications, no live mutations were performed.

| Layer | Task ID | Profile | Artifact | Scope |
|-------|---------|---------|----------|-------|
| Synthesis | t_2d568471 | software-architect | `V4-LOCAL-SYNTHESIS-REPORT_1.md`, `synthesis-metadata.json` | Reconciles all parents with Advanced Research baseline |
| Profiles | t_c2257b50 | investigator | `V4-LOCAL-PROFILES-INVESTIGATION.md`, `profile-evidence.json` | 14 profiles, spawnability, toolsets, docs/runtime |
| Skills | t_2d78d03f | profile-architect | `V4-LOCAL-SKILLS-INVESTIGATION_1.md` | 53 enabled skills, origins, sdlc-review force-load |
| CLI | t_59a2a2f5 | operator | `findings.txt` | 74 top-level commands, 47 kanban subcommands |
| Config | t_ef94f514 | investigator | `V4-LOCAL-CONFIG-report.md` | SQLite schema, workspace/branch precedence, dispatch controls |
| Runtime | t_ad6925aa | investigator | `V4-LOCAL-RUNTIME-report.md` | Gateway, dispatcher, workers, runs, build provenance |
| Attachments | t_2499ad0a | investigator | `REPORT-t_2499ad0a-attachments-contract.md` | Attachment contract, size caps, base64 gap |
| Native Tools | t_5caf4595 | investigator | `native_tools_inventory.json`, `native_tools_inventory_report.md` | 87 leaf tools across 31 toolsets |

---

## 2. Version & Environment Baseline

| Property | Value |
|----------|-------|
| Hermes Version | v0.20.2 (2026.8.16) |
| Source HEAD | 39cfd1ab41 (+2 carried commits, upstream b7bed241) |
| Install Path | /home/ubuntu/hermes-agent (git install) |
| Board | hermes-chatgpt-mcp |
| Deployment label | `Kanban_Beta` (stale metadata; controller classifies deployment as STABLE) |
| Deployed connector SHA | **STILL_NOT_PROVEN** |

---

## 3. Profile Inventory (14 total)

**Observed spawnable (end-to-end):**
- `investigator`
- `profile-architect`
- `operator`
- `software-architect`

**Dispatcher-eligible (predicate-level, 10 INFERRED_ONLY):**
- `coder`
- `reviewer`
- `researcher`
- `writer`
- `planner`
- `analyst`
- `tester`
- `architect`
- `debugger`
- `default`

**Note:** `spawnable` distinguishes `dispatcher_eligible` (predicate-level) from `end_to_end_observed` (only 4 profiles confirmed). `effective_toolsets` uses runtime resolved values, not legacy top-level `toolsets:` field (P1-1 recommendation).

---

## 4. Skill Inventory (53 enabled on default profile)

| Origin | Count | Notes |
|--------|-------|-------|
| builtin | 39 | Core Hermes skills |
| local | 14 | User-installed in `~/.hermes/profiles/default/skills/` |
| hub | 0 | None currently installed |

**CRITICAL CONSTRAINT:** V4 skill queries MUST use `skills list` or `skill_view`, never `hermes skills inspect` — inspect is hub-only and cannot resolve builtin/local skills (P0-4).

**sdlc-review caveat:** `sdlc-review` is builtin, dispatcher force-loaded into review workers at dispatch time (`kanban_db.py:10384`), but absent from reviewer profile's local skills. `skills inspect` limitation means it cannot be discovered via inspect.

---

## 5. CLI Inventory

| Category | Count | Notes |
|----------|-------|-------|
| Top-level Hermes commands | 74 | Includes `hermes kanban` as one entry |
| Kanban subcommands | 47 | Registered in CLI parser |

**Registration ≠ Operational PASS:** `--help` registration proves the command exists in the CLI parser. It does NOT prove operational PASS for every leaf subcommand. Actual leaf behavior is only proven where a real safe read call, prior board evidence, or MCP E2E test exists.

---

## 6. Native Tool Registry

| Metric | Value |
|--------|-------|
| Unique leaf tools | 87 |
| Registry toolsets | 31 |
| Static toolsets (legacy `toolsets:` field) | 59 |
| Builtin origin | 87 |

**Important:** 87 native leaf registry ≠ blanket operational availability. Runtime effective toolsets (not legacy `toolsets:`) determine what's actually available per profile.

---

## 7. MCP Connector Live Discovery (Operator-authoritative, 2026-08-19)

**Current read/introspection tools exposed (18):**
`list_boards`, `get_board`, `list_tasks`, `get_task`, `get_task_graph`, `get_dispatch`, `get_activity`, `diagnostics`, `attachments`, `stats`, `log`, `runs` (task-scoped), `assignees`, `context`, `tail`, `watch`, `daemon` (status/snapshot only), `notify-list`

**Current write/action tools exposed (36):**
`create_task`, `create_board`, `add_comment`, `assign_task`, `link_tasks`, `unlink_tasks`, `set_model`, `reclaim_task`, `reassign_tasks`, `complete_tasks`, `edit_task` (COMPLETED TASK RESULT only), `block_tasks`, `schedule_tasks`, `unblock_tasks`, `request_review`, `request_changes`, `reopen_review`, `promote_tasks`, `archive_tasks`, `claim`, `attach` (local_path only), `attach-rm`, `heartbeat`, `specify`, `init`, `swarm`, `dispatch`, `decompose`, `gc`, `repair`, `notify-subscribe`, `notify-unsubscribe`, `boards-rm`, `boards-switch`, `boards-rename`, `boards-set-default-workdir`

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

**Exposure ≠ Validation:** Operator-authoritative discovery proves `current_exposure` only — it NEVER constitutes validation. `AVAILABLE_VALIDATED` requires real invocation evidence (actual tool call in this docs session or prior board QA). Discovery-only tools are classified `NOT_PROVEN` for behavioral status even when exposed on the live surface.

---

## 8. Current Proven OAuth Scopes

| Scope | Proven For | Evidence |
|-------|------------|----------|
| `hermes:read` | All read-only tools (baseline) | Implicit in MCP connection |
| `hermes:create` | `create_task` only | Live schema / board QA |
| `hermes:manage` | `add_comment`, `assign_task` only | Live schema / board QA |
| `hermes:board:create` | `create_board` only | Live schema |
| `offline_access` | Connection flow only — refresh token | Not a tool scope |

**NOT_PROVEN / inherited policy** applies to all other tools' current_scope. Do not assume `hermes:create` covers comments or attachments, or that `hermes:manage` covers all writes — each tool's current scope must be individually proven from live schema or invocation evidence.

---

## 9. Proposed V4 Fine-Grained Scopes (PROPOSED — not current)

| Proposed Scope | Maps From Current | Intended Use |
|----------------|-------------------|--------------|
| `hermes:task:read` | `hermes:read` | Read tasks, task graphs, activity |
| `hermes:task:create` | `hermes:create` | Create tasks |
| `hermes:task:write` | `hermes:manage` | Edit, complete, promote, block, unblock, request_review |
| `hermes:comment:create` | `hermes:create` | Add comments |
| `hermes:attachment:read` | `hermes:read` | List and download attachments |
| `hermes:attachment:create` | `hermes:create` | Upload attachments |
| `hermes:attachment:delete` | `hermes:manage` | Remove attachments |
| `hermes:profile:read` | `hermes:read` | List and get profiles, skills |
| `hermes:worker:read` | `hermes:read` | List workers, get runs, inspect runs |
| `hermes:worker:terminate` | `hermes:manage` | Terminate runs |
| `hermes:gateway:read` | `hermes:read` | Gateway and dispatcher status |
| `hermes:tool:read` | `hermes:read` | Native tool registry, profile tools |
| `hermes:config:read` | `hermes:read` | Kanban config |
| `hermes:config:write` | `hermes:manage` | Update Kanban config |
| `hermes:board:read` | `hermes:read` | List boards |
| `hermes:board:create` | `hermes:board:create` | Create boards (unchanged) |
| `hermes:notification:read` | `hermes:read` | Poll notifications |
| `hermes:notification:create` | `hermes:create` | Subscribe to notifications |

**Migration mapping (CURRENT → PROPOSED):**
- `hermes:read` → `hermes:task:read`, `hermes:attachment:read`, `hermes:profile:read`, `hermes:worker:read`, `hermes:gateway:read`, `hermes:tool:read`, `hermes:config:read`, `hermes:board:read`, `hermes:notification:read`
- `hermes:create` → `hermes:task:create`, `hermes:comment:create`, `hermes:attachment:create`, `hermes:notification:create`
- `hermes:manage` → `hermes:task:write`, `hermes:attachment:delete`, `hermes:worker:terminate`, `hermes:config:write`
- `hermes:board:create` → `hermes:board:create` (unchanged)

**Note:** V4 tools use CURRENT scope names. Any implementation adopting PROPOSED scopes MUST provide backward compatibility via scope aggregation.

---

## 10. Attachment Contract (Current vs V4)

| Aspect | Current (Agent) | Current (MCP Connector) | V4 Target |
|--------|-----------------|-------------------------|-----------|
| Upload method | `content_base64` (agent tool) | `local_path` only (SERVER_LOCAL_BOUND) | `content_base64` + `local_path` |
| Size cap | 25 MB (`KANBAN_ATTACHMENT_MAX_BYTES`) | 10 MB (`MCP_MAX_ATTACHMENT_BYTES` default) | Unified 25 MB |
| Remote upload | Supported (agent) | **MISSING** — remote clients cannot provide server-local paths | Required |

**P0-1 resolution:** Current MCP `attach(local_path=...)` is architecturally wrong for remote clients — it requires server filesystem access that remote clients cannot provide. V4 MUST add `content_base64` field. The `local_path` variant is retained for server-side automation only.

**P0-2 resolution:** Size cap must be unified to 25MB across all surfaces. Document divergence until connector is updated.

---

## 11. Remaining Uncertainty (Explicitly Preserved)

| Item | Classification | Notes |
|------|----------------|-------|
| Temporary per-task skill resolution | NOT_PROVEN | Partial resolution; depends on profile contents |
| Fine-grained profile permissions enforcement | NOT_PROVEN | No enforcement path found in Hermes core; `capabilities/refuses` advisory only |
| Historical C-IMPL-5 crash cause | NOT_PROVEN | Historical; not safety-relevant for current contract |
| Managed overlay / effective controller config | NOT_PROVEN | Runtime config composition not fully mapped |
| Live SQLite schema dump | NOT_PROVEN | Schema known from source; live instance not dumped |
| Deployed connector SHA | STILL_NOT_PROVEN | Integration concern |
| Live HTTP/API auth and reachability | STILL_NOT_PROVEN | Dashboard/native API endpoints |
| Provider/model validity | NOT_PROVEN | Runtime resolution not verified |
| Native MCP/plugin/dynamic tool registration | NOT_PROVEN | Tool registration surface not fully mapped |
| Live slash/terminate/heartbeat-retry behavior | UNSAFE_TO_TEST | Would mutate production state |

---

## 12. Dogfood Incidents (This Docs Program)

1. **Post-complete artifact freeze** (t_484d4ab0): `kanban_complete` freezes durable result/artifacts; later workspace edits must NOT silently mutate completed artifacts. Corrections require explicit reissue/versioning.
2. **t_343 nonconvergence:** Prior roadmap tasks failed to converge on scope/vocabulary; superseded by t_8a7b081c.
3. **t_702 integration/stash incident:** Prior integration worker (t_70297725) created a pre-safety stash; dirty main checkout left unmodified per safety rules.
4. **Discovery vs stale checkout:** Live connector discovery (54 tools) vs checked-out repo state (older schemas) — canonical docs must reconcile, not assume checkout is truth.
5. **get_board capability inconsistency:** `get_board` capability readback inconsistent with successful writes (known issue).
6. **Manual dispatch BACKEND_ERROR:** `dispatch` tool exists but manual call observed `BACKEND_ERROR` => inconsistent.

---

## 13. Product Status Vocabulary (Exact)

| Code | Emoji | Meaning |
|------|-------|---------|
| AVAILABLE_VALIDATED | ✅ | Registered in CLI, exercised via safe read call or board evidence, behavior confirmed |
| AVAILABLE_INCONSISTENT | ⚠️ | Registered but known defect/inconsistency documented |
| IN_PROGRESS | 🔧 | Actively being implemented in current development cycle |
| PLANNED_V4 | 🗓️ | Designed for V4 release, not yet implemented |
| PLANNED_V4X | 🗓️+ | Designed for post-V4 minor release |
| PLANNED_V5 | 🗓️2 | Designed for next major version |
| NOT_AVAILABLE | ❌ | Not present, no active plan |
| NOT_PROVEN | ❓ | Registered/exists but behavior not exercised; only registration or discovery evidence |
| UNSAFE_TO_TEST | 🔒 | Would mutate production state (terminate, slash invocation, live kill) |
| NOT_APPLICABLE_MCP | N/A | Not relevant to MCP connector surface |

---

## 14. Priority Codes

| Code | Meaning |
|------|---------|
| P0 | Blocking for V4 release |
| P1 | Important for V4, non-blocking |
| P2 | Nice to have for V4 |
| P3 | Deferred |
| DO_NOT_EXPOSE | Must not be exposed via MCP/connector |

---

## 15. Cross-References

- **Spec/ADR:** [CONTROL_PLANE_SPEC.md](CONTROL_PLANE_SPEC.md) | [MCP_TOPOLOGY_ADR.md](MCP_TOPOLOGY_ADR.md)
- **Catalog:** [TOOL_CATALOG.md](TOOL_CATALOG.md) | [v4-tool-catalog.json](v4-tool-catalog.json)
- **Matrices:** [KANBAN_CLI_MATRIX.md](KANBAN_CLI_MATRIX.md) | [HERMES_CAPABILITIES_MATRIX.md](HERMES_CAPABILITIES_MATRIX.md)
- **Planning:** [ROADMAP.md](ROADMAP.md) | [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | [DOGFOOD_QA_PLAN.md](DOGFOOD_QA_PLAN.md)
- **Evidence:** [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) | [STALE_DOCS.md](STALE_DOCS.md)