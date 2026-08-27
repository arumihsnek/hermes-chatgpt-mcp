# V4 Current State — Canonical Source of Truth

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE + **V4 STABLE ACCEPTED 2026-08-27**
**Last reconciled:** 2026-08-19 (canonical design) + **2026-08-21 release-candidate truth-sync** (see [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md)) + **2026-08-25 current-truth freshness** (see [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)) + **2026-08-25 DAG soft-retire contract** (see [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)) + **2026-08-27 V4 stable truth-sync** (see [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) + [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md))
**Documentation base (pre-V4-stable design docs):** 9900c10 (local ref only; pre-V4 beta worktree — **NOT** the V4 stable commit)
**V4 stable connector (durable binding):** `4ae5060931a64741185c5c8deb3886a5901f21cc` (short `4ae5060`, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`, Hermes Core MCP baseline `d7eba25ea8f6`)
**See also:** [README.md](README.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) | [RECOVERY-TRUTH-SYNC-2026-08-24.md](RECOVERY-TRUTH-SYNC-2026-08-24.md) | [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) | [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md)

---

## 0. CURRENT TRUTH PRECEDENCE (cold-start rule)

Before answering "where are we now?", rank sources highest-authority first. A lower rank NEVER overrides a higher one; on conflict, mark the lower **STALE** before citing.

1. live runtime / service readback (live MCP discovery, `/healthz`, read probes, public E2E — captured **at execution time**)
2. live canonical Kanban state / latest runs / events
3. fresh immutable evidence bound to exact SHA / run id
4. current Git HEAD / worktrees / refs
5. current checkpoints / manifests (dated snapshots)
6. current repo docs (this `docs/v4` set at its base)
7. historical terminal cards (superseded ancestors are NOT current authority)
8. archived / superseded cards
9. old docs (v0.1 / v0.3 / v0.4, pre-V4)
10. project / harness memory
11. inference

A checked-out doc tree is **not** automatically truth; discovery ≠ validation; a stale checkout is not the runtime. Full ladder + cold-start protocol + Project Model vs Current State Vector split: [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md).

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
| Source HEAD | 39cfd1ab41 (+2 carried commits, upstream b7bed241) — **pre-V4-stable design-docs base** |
| Install Path | /home/ubuntu/hermes-agent (git install) |
| Board | hermes-chatgpt-mcp |
| **V4 stable connector (durable binding, 2026-08-27)** | `4ae5060931a64741185c5c8deb3886a5901f21cc` (branch `v4-candidate-integration`) — **RESOLVED** from prior `STILL_NOT_PROVEN` |
| **V4 stable surface** | `beta` (controller classifies the deployment as STABLE; `Kanban_Beta` discovery label is stale naming metadata) |
| **V4 stable API surface** | `v4.wave0` (response header `x-api-version`; durable contract identifier) |
| **Hermes Core MCP baseline** | `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` (header short `d7eba25ea8f6`; branch `v4/baseline-post-update-885e9ef`) |
| **Live MCP `tools/list` tool count** | **71** (vs the 2026-08-19 54-tool discovery; updated by `4ae5060` Wave-0-to-4 integration) |
| **v4.wave0 required tools (all 6 present)** | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` |
| **Stable runtime** | `/opt/venvs/hermes-chatgpt-mcp` (venv) + `/opt/hermes-chatgpt-mcp-canary` (override-redirected 8789 working dir; same `4ae5060` image) |
| **Public MCP origin** | `https://kanban.hermesinthenight.duckdns.org/mcp` (OpenResty forwards to `127.0.0.1:8789`) |
| **Deployed-at (build.json)** | `2026-08-26T14:34:00Z` — canary's original deploy time, **not** the 2026-08-27 R2 cutover time (residual; see [CHECKPOINT-2026-08-27-V4-STABLE.md §6](CHECKPOINT-2026-08-27-V4-STABLE.md)) |

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
| **Deployed connector SHA** | **RESOLVED 2026-08-27** — was `STILL_NOT_PROVEN`; now `4ae5060931a64741185c5c8deb3886a5901f21cc` (V4 stable, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`) | See [CHECKPOINT-2026-08-27-V4-STABLE.md §0](CHECKPOINT-2026-08-27-V4-STABLE.md) and [EVIDENCE_AND_OPEN_QUESTIONS.md §2](EVIDENCE_AND_OPEN_QUESTIONS.md) (removed from `STILL_NOT_PROVEN` table) |
| **Live HTTP/API auth and reachability** | **PARTIALLY RESOLVED 2026-08-27** — public origin `https://kanban.hermesinthenight.duckdns.org` reachability proven for `/healthz`, `/mcp` (401 with bearer challenge), and OAuth discovery; full native API surface (dashboard plugin mount, native Hermes REST, etc.) remains `STILL_NOT_PROVEN` | See [CHECKPOINT-2026-08-27-V4-STABLE.md §1a](CHECKPOINT-2026-08-27-V4-STABLE.md) for the live readback evidence |
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
7. **DAG edge_state soft-retire (PROJECTION_RUNTIME_P0):** runtime `165d1849e25c` is edge_state-blind in `parent_ids`/`child_ids`/`task_graph_context`/`recompute_ready`/`_parents_satisfied`/`claim_task`/MCP fallback; `retired`/`rebound` edges still exert gating power. Canonical contract: [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md).
8. **Fixture leakage dogfood (PASS):** `t_a161305b`/run1114 and `t_85b5b14b`/run1118 created with `pid999999`/`boom`/`worker` on canonical board; reclaimed+archived canonically, no DELETE, review PASS. Root = `gave_up`+`promoted` without atomic run/claim closure + test isolation failure.

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

## 15. Release-Candidate Truth-Sync (2026-08-21)

This section overlays the live Kanban release-candidate state onto the canonical design above. The canonical design (sections 1–14, dated 2026-08-19) remains authoritative for architecture/scope. Current task status always comes from Kanban; see [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md) for the full reconciliation.

- **Immediate Phase-S blocker:** G1 (outcome-aware dependency authorization). All other G2–G20 are *not* wholesale beta blockers per the 2026-08-21 triage (`t_72108336` comment 579).
- **Outcome-gate recovery chain:** `t_b0901b4a` (gave-up, partial) → `t_c4c38028` (freeze candidate, running) → `t_09f51d5a` (adversarial/race, todo) → `t_8c125abe` (reactivate review, todo) → `t_fc541b39` (independent ACCEPT, blocked) → `t_7c2f0fdd` (real-board dogfood, todo). Gate closeout is **NOT_PROVEN** until `t_fc541b39` ACCEPT + `t_7c2f0fdd` proof.
- **Provenance:** `t_415df0f5` PASS (independent review); `t_dadd5ebf` fresh provenance **GO** — evidence only, **NOT release/build/deploy authorization**.
- **Hold rebind:** current authority `t_e187bee7` (depends on `t_7c2f0fdd` + `t_dadd5ebf`); `t_e1b6bae8` is HISTORICAL/SUPERSEDED for the current chain (not deleted, not current authority).
- **Canary handshake:** `t_be036abf` requires a fresh MCP/OAuth session + observed receipt (canary/release ID, Connector SHA, Core SHA/version, schema/tool-surface version, scopes actually granted/effective) before first mutation; mismatch/unknown identity ⇒ FAIL.
- **Deployed connector SHA** remains **STILL_NOT_PROVEN**; must be pinned at clean-build identity (next semantic checkpoint), not claimed here.

## 15b. DAG / Projection Soft-Retire Release Blocker (2026-08-25)

The `task_links.edge_state` soft-retire contract (`active|retired|rebound`; retired/rebound carry zero gating power; provenance fields are historical evidence only) and its deployment invariant are canonical at [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md). Current release blocker: runtime `165d1849e25c` is edge_state-blind (PROJECTION_RUNTIME_P0). Release path (fail-closed): deploy edge-aware runtime under fresh Human Gate + live readback → fresh upstream acceptance replacing historical `t_47fcecec` if required → open `barrier` → V4-CUT3. Do NOT delete retired edges or complete `barrier` for throughput. Current lanes: `t_31d1c67f` implementation, `t_20dd938c` review, `t_ef3ae8d4` activation-gate-prep; `barrier`/V4 remain closed.

## 16. Cross-References

- **Spec/ADR:** [CONTROL_PLANE_SPEC.md](CONTROL_PLANE_SPEC.md) | [MCP_TOPOLOGY_ADR.md](MCP_TOPOLOGY_ADR.md)
- **Catalog:** [TOOL_CATALOG.md](TOOL_CATALOG.md) | [v4-tool-catalog.json](v4-tool-catalog.json)
- **Matrices:** [KANBAN_CLI_MATRIX.md](KANBAN_CLI_MATRIX.md) | [HERMES_CAPABILITIES_MATRIX.md](HERMES_CAPABILITIES_MATRIX.md)
- **Planning:** [ROADMAP.md](ROADMAP.md) | [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | [DOGFOOD_QA_PLAN.md](DOGFOOD_QA_PLAN.md)
- **Evidence:** [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) | [STALE_DOCS.md](STALE_DOCS.md) | [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)
- **Current-truth freshness (2026-08-25):** [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md) — Source Precedence Ladder, cold-start protocol, Project Model vs Current State Vector, dogfood finding
- **V4 stable release provenance (2026-08-27):** [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md) — durable release anchor (SHAs, header values, topology, rollback, residuals). **The canonical current-state answer for "what is the V4 stable?" lives here.**
- **V4 stable truth-sync checkpoint (2026-08-27):** [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) — full reconciliation: live readback, topology narrative, rollback path, residuals register, dogfood lessons, cross-references.

---

## 17. V4 Stable Reconciliation — 2026-08-27

This section overlays the **V4 stable acceptance** (parent task `t_1e84eb11` ACCEPT 2026-08-27) onto the canonical design above. Sections 1–16 remain authoritative for architecture / scope / design intent. The V4 stable identity is now bound to a durable SHA and **supersedes** the prior `STILL_NOT_PROVEN` claims for the deployed connector. The full evidence chain — live readback, on-disk SHA-256 manifest pins, all 8 prerequisites, the rollback path, and the residuals register — lives in [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) and the short anchor [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md). The current section is the **one-page summary** for readers who already know the canonical design and just need to know the V4 stable truth.

### 17.1 Identity (the V4 stable)

| Identity | Value | Evidence |
|----------|-------|----------|
| Connector (V4 stable commit) | `4ae5060931a64741185c5c8deb3886a5901f21cc` (short `4ae5060`) | `v4-candidate-integration` branch head, 2026-08-26T14:01:53Z |
| Phase-S source bundle | `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` (short `9a8410b4`) | `release/source-bundle-phase-s` branch head |
| Hermes Core MCP baseline | `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` (header short `d7eba25ea8f6`) | response header `x-baseline-mcp` |
| Hermes Core baseline branch | `v4/baseline-post-update-885e9ef` (short `885e9ef73829`) | response header `x-baseline-branch` |
| Phase-S short SHA | `ef22b89e8b49` | parent `t_1e84eb11` handoff |
| Surface (build.json) | `beta` (controller classifies the deployment as STABLE; `Kanban_Beta` discovery label is stale naming metadata) | build.json `surface` + response header `x-v4-provenance` |
| API surface version | `v4.wave0` | response header `x-api-version` |
| Live V4 provenance header | `4ae5060931a6/d7eba25/beta` | response header `x-v4-provenance` |
| Live MCP `tools/list` tool count | **71** | post-switch smoke `t_a47fd88f` contract check #10 |
| v4.wave0 required tools (all 6 present) | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` | `t_a47fd88f` contract check #10 |

### 17.2 Live readback (captured 2026-08-27 21:31 UTC)

All three live surfaces — stable loopback `127.0.0.1:8789`, public origin `https://kanban.hermesinthenight.duckdns.org`, and canary loopback `127.0.0.1:8792` — report **identical** identity headers: `4ae5060931a64741185c5c8deb3886a5901f21cc` / `surface=beta` / `deployed_at=2026-08-26T14:34:00Z`, with `x-v4-provenance: 4ae5060931a6/d7eba25/beta`, `x-api-version: v4.wave0`, `x-baseline-branch: v4/baseline-post-update-885e9ef`, `x-baseline-mcp: d7eba25ea8f6`.

The on-disk SHA-256 manifest pins (R2 manifest) match exactly:

- `/var/lib/hermes-chatgpt-mcp/build.json` → `b83efaea3d253074f546661da4f27cfc0b4a579adad3d0f45fc48f2f0e2a231e` (full; R2 short `b83efaea…231e`)
- `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` → `d8d87c59817cfce591fd0a9bfcd54898534f84c96d1d461e1fbf8ffed8d1d90a` (full; R2 short `d8d87c59…1d90a`)
- `/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-subdomains.conf` → `b9d2daa9b5a420db2142f9ef2644ba4d9e239d5b4b959fca0bd5e0c0f5ae187b` (full; R2 short `b9d2daa9…187b`, **unchanged across the cutover**)
- `/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-chatgpt-mcp.locations` → `27caf8746d8eb44b18492c48f041bfd0c90a2f965749bae246e6d824efb0c816` (full; R2 short `27caf874…0816`, **unchanged across the cutover**)

### 17.3 Deployment topology (V4 stable runtime)

| Surface | Loopback | Process | Working dir | Public route | Identity |
|---------|----------|---------|-------------|---------------|----------|
| Stable (public) | `127.0.0.1:8789` | `hermes-chatgpt-mcp.service` (MainPID 2505228) | `/opt/hermes-chatgpt-mcp-canary` (override-redirected) | OpenResty `hermes-chatgpt-mcp.locations` (SHA-256 `27caf874…0816`, unchanged) | `4ae5060931a6` / `beta` / `v4.wave0` |
| Canary (isolated) | `127.0.0.1:8792` | `hermes-chatgpt-mcp-canary.service` (MainPID 2506251) | `/opt/hermes-chatgpt-mcp-canary` | none (systemd disabled; no public route) | `4ae5060931a6` / `beta` / `v4.wave0` |
| Pre-V4 `8791` beta | **not running** | dormant | n/a | n/a | n/a — superseded by the canary + 8789 override model |

The 8789 stable is running the canary venv+WD via the override drop-in (`d8d87c59…1d90a`); the systemd unit, env file (`/home/ubuntu/.hermes/hermes-chatgpt-mcp.env`, mtime 2026-08-18, pre-promotion, **untouched**), state paths, and port 8789 are preserved. The pre-V4 `8791` beta deployment unit (`hermes-chatgpt-mcp-beta.service`) still exists on disk but is **not part of the V4 stable runtime**; resurrecting it requires fresh authorization.

### 17.4 Rollback path (executable, byte-anchored, no installer run)

The V4 stable rollback is **three reversible mutations only** — the same three items the parent `t_1e84eb11` enumerated:

1. **Delete the override drop-in** at `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` (`d8d87c59…1d90a`).
2. **Restore the prior-good `build.json`** from the in-place backup `/var/lib/hermes-chatgpt-mcp/build.json.pre-surface-rectification-20260826T103951Z.bak` (commit `d7eba25ea8f6`, surface `stable`, deployed_at `2026-08-25T15:13:56Z`).
3. **One bounded `systemctl restart hermes-chatgpt-mcp.service`** (the only restart; no daemon-reload, no OpenResty reload).

No installer run, no wheel re-hash, no OAuth state rewrite, no credential rotation, no OpenResty mutation, no schema migration. The pre-promotion venv `/opt/venvs/hermes-chatgpt-mcp` is on disk (mtime 2026-08-17) and is reused. The pre-promotion env file is on disk and is reused. OAuth state is **not** touched by the V4 stable cutover, so all DCR clients and refresh-grant records remain valid in both directions. The rollback is **safe to execute** without re-validation; the prior-good identity passed the full MCP E2E + dogfood chain under the v0.4 contract.

### 17.5 Pre-flight invariants (all PASS, re-verified 2026-08-27)

The 8 prerequisites of the parent `t_1e84eb11` ACCEPT chain are all PASS independently:

| # | Prerequisite | Source | Status |
|---|--------------|--------|--------|
| 1 | Clean build reproducible | `t_da03fbe7` 221/221 in fresh `/tmp/hermes-v4-build` py3.11.15 | ✅ |
| 2 | Canary deploy isolated | `t_56187ec4` 8792 systemd disabled, full isolation matrix | ✅ |
| 3 | Real MCP E2E | `t_5a9c43f7` 77/77 PASS OAuth/DCR PKCE S256 + refresh rotation + board-scoped grants + dispatch realism on `hermes-chatgpt-e2e-04780a62` | ✅ |
| 4 | Wave 0-4 carry-forward | W0 13/13, W1 13/13, W2 20/20, W3 15/15, W4 15/15, integration 221/221 (`t_068740be` + `t_f96589bf`) | ✅ |
| 5 | Extended dogfood | `t_45647dc7` 88/1 with F-DOGFOOD-01 LOW non-blocking; full DIAGNOSE→FIX→REVIEW→REGRESSION→RETEST chain closed | ✅ |
| 6 | Incident attestation | `t_ae8e6c64` NONE — zero release-blocking incidents; full chain `t_7afc509f`→`t_a0d6bae7`→`t_ed301a4c`→`t_aad72b38`→`t_a343fc54` all done | ✅ |
| 7 | Human gates | G2 `t_5b1757e2` YES (4ae5060, R2 manifest, `9d051d19` nonce) + G3 `t_bae2e48b` YES (`4745f2cd` manifest, `b51d1f91` nonce) + R3B `t_35a9e6b0` YES (continue from applied state, scope-limited) | ✅ |
| 8 | Traffic switch | `t_5a7cf41c` state verified under R3B; promotion manifest sha256 `e5ffbf2c…94ba1`; immutable public routing preserved | ✅ |

### 17.6 Known residuals (documented, non-blocking)

| # | Residual | Severity | Source |
|---|----------|----------|--------|
| 1 | F-DOGFOOD-01 `bounded_log` cursor `BACKEND_ERROR` (additive convenience only) | LOW, fail-closed | `t_45647dc7` extended dogfood |
| 2 | W0 Low `initialize` 1999-01-01 negotiates 2025-11-25 | LOW | `t_068740be` independent review |
| 3 | Ephemeral worker venv `hermes_cli` `ModuleNotFoundError` (canary venv only) | LOW | canary-side observation |
| 4 | `deployed_at` reports canary's original deploy time, not 2026-08-27 cutover time | Informational | `t_a47fd88f` POST_SWITCH_REPORT |
| 5 | No `/opt/hermes-chatgpt-mcp` (stable checkout dir); rollback uses venv only | Informational | `t_1e84eb11` parent handoff |
| 6 | Pre-V4 `hermes-chatgpt-mcp-beta.service` (8791) dormant in V4 stable topology | Informational | live readback (no process on 8791) |

### 17.7 Stale claims removed (with evidence)

| Prior claim | Prior evidence | Now | Evidence |
|-------------|----------------|-----|----------|
| `Deployed connector SHA: STILL_NOT_PROVEN` | design-doc baseline only (9900c10 is pre-V4 beta worktree) | `4ae5060931a64741185c5c8deb3886a5901f21cc` (V4 stable, branch `v4-candidate-integration`) | live readback (3 surfaces, all 4 headers match); 4 on-disk SHA-256 manifest pins matching R2; 8/8 prerequisites PASS |
| `Live MCP tool count: 54` (2026-08-19 discovery) | design-doc baseline only | **71** (post-Wave-0-to-4 integration at `4ae5060`) | post-switch smoke `t_a47fd88f` contract check #10 |
| `Kanban_Beta` discovery label is "stale metadata; controller classifies deployment as STABLE" | design-doc narrative | unchanged in narrative; the **build.json `surface` value is now `beta`** (not `stable`) — controller still classifies as STABLE, but the **on-disk surface label is `beta`** (documented residual, no contract violation) | live readback; `t_a47fd88f` POST_SWITCH_REPORT residual note |

### 17.8 Historical context (preserved, not silently corrected)

- The 2026-08-19 design baseline (`Documentation base: 9900c10`, `Hermes Version: 0.20.2`, `Source HEAD: 39cfd1ab41`, `live_mcp_discovery_tools: 54`) is **not deleted**; it is preserved as the **historical design baseline** that the V4 stable was built on. The 2026-08-25 DAG soft-retire contract, the 2026-08-25 current-truth freshness checkpoint, the 2026-08-24 recovery truth-sync, and the 2026-08-21 release-candidate truth-sync are all preserved unchanged in their original sections.
- The v0.4 `8791` deployment topology described in `docs/DEPLOYMENT.md` and `docs/SECURITY.md` is **not silently corrected**; it is preserved as **dated v0.4 contract** in [STALE_DOCS.md](STALE_DOCS.md) and re-classified in the v0.4 sections as **RETAIN / LINK; SUPERSEDE for current runtime**. A new `## V4 stable runtime (2026-08-27)` section in those files points readers at this checkpoint.
- The `STILL_NOT_PROVEN` items unrelated to the V4 stable cutover (live HTTP/API auth for native API, provider/model validity, dynamic tool registration, etc.) are **not silently marked resolved**; they are preserved in §11 with their prior `NOT_PROVEN` classification and explicit cross-references to where the resolved items are now bound.

### 17.9 Authority note

The V4 stable identity above is **authoritative for the V4 stable runtime**. It is **not** a new design, **not** a new architecture, **not** a new product-scope change. It is the durable binding of an already-accepted V4 stable. Any future V4.x cutover (e.g. `4ae5060+x` connector, `d7eba25+y` MCP baseline, `v4.wave1` API surface) must be bound by a new truth-sync checkpoint in this `docs/v4` set, with the same live-readback + SHA-pinned + 8-prereq pattern, before it can be cited as current runtime.
