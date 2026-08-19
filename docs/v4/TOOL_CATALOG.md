# V4 MCP Tool Canonical Catalog

**Date:** 2026-08-19
**Author:** software-architect (t_1419658e) (integrated by github-steward task t_70297725)
**Evidence baseline:** Hermes v0.20.2 (2026.8.16), source HEAD 39cfd1ab41
**Evidence tasks:** t_1419658e (tool catalog), t_484d4ab0 (spec/ADR), t_4ce4ba8f (matrices), t_4d983898 (SoT), t_8a7b081c (roadmap/implementation/dogfood)
**Status:** CANONICAL — integrated into docs/v4/ as part of V4 documentation
**Topology:** Single MCP server with internally privilege-separated adapters (ADR t_484d4ab0)

---

## Scope Vocabulary (exact product vocabulary)

| Status Code | Display | Meaning |
|-------------|---------|---------|
| AVAILABLE_VALIDATED | ✅ DISPONIBLE Y VALIDADO | Real invocation evidence: behavior confirmed via actual tool call in this session or prior board QA |
| AVAILABLE_INCONSISTENT | ⚠️ DISPONIBLE CON ERRORES / INCONSISTENCIAS | Live surface present but known defect or BACKEND_ERROR documented |
| IN_PROGRESS | 🚧 EN TRABAJO | Actively being implemented in current cycle |
| PLANNED_V4 | 🗓️ PLANIFICADO V4 | Designed for V4 release, not yet implemented |
| PLANNED_V4X | 🗓️ PLANIFICADO V4.x | Designed for post-V4 minor release |
| PLANNED_V5 | 🗓️ PLANIFICADO V5 | Designed for next major version |
| NOT_AVAILABLE | ⛔ NO DISPONIBLE / NO PLANIFICADO | Not present, no active plan |
| NOT_PROVEN | ❓ NOT_PROVEN | Tool exists in source/CLI but behavior not exercised; only registration or discovery evidence |
| NOT_APPLICABLE_MCP | ➖ NO APLICA AL MCP | Not relevant to MCP connector surface |

**CRITICAL DISTINCTION:** `operator_authoritative_discovery` (live surface listing) proves `current_exposure` only — it NEVER constitutes validation. `AVAILABLE_VALIDATED` requires real invocation evidence (actual tool call in this docs session or prior board QA). Discovery-only tools are classified `NOT_PROVEN` for behavioral status even when exposed on the live surface.

## Priority Codes

| Code | Meaning |
|------|---------|
| P0 | Blocking for V4 release — full feature scope |
| P1 | Important for V4, non-blocking |
| P2 | Nice to have for V4 |
| P3 | Deferred |
| DO_NOT_EXPOSE | Must not be exposed via MCP — risk-based |

## Current Proven OAuth Scopes (row-specific, explicit only)

These are the scopes **explicitly proven** by live schema inspection or invocation evidence in this documentation session. Current scope for other tools is marked `NOT_PROVEN / inherited policy` — do NOT infer scope by operation type.

| Scope | Proven For | Evidence |
|-------|-----------|----------|
| `hermes:read` | All read-only tools (baseline) | Implicit in MCP connection |
| `hermes:create` | `create_task` only | Live schema / board QA |
| `hermes:manage` | `add_comment`, `assign_task` only | Live schema / board QA |
| `hermes:board:create` | `create_board` only | Live schema |
| `offline_access` | Connection flow only — refresh token | Not a tool scope |

**NOT_PROVEN / inherited policy** applies to all other tools' current_scope. Do not assume `hermes:create` covers comments or attachments, or that `hermes:manage` covers all writes — each tool's current scope must be individually proven from live schema or invocation evidence. See per-tool `current_scope` field in both this document and the JSON catalog.

## Proposed V4 Fine-Grained Scopes (PROPOSED — not current)

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

---

## P0 — Blocking for V4 Release

### P0.1 Profiles / Skills Discovery

#### `list_profiles`

| Field | Value |
|-------|-------|
| **Domain** | Profiles / Skills |
| **Purpose** | List all installed Hermes profiles with metadata |
| **Inputs** | `{}` (empty; board scope implicit from session) |
| **Outputs** | `{ items: [{ name, description, model_provider, skill_count, effective_toolsets, disponible, spawnable }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `hermes profile list`) |
| **V4 proposed contract** | `list_profiles` |
| **Primitive** | `hermes_cli.profiles.list_profiles()` + `hermes_cli.tools_config._get_platform_tools()` |
| **Validation** | None (pure read) |
| **Errors** | `BOARD_NOT_FOUND`, `INTERNAL_ERROR` |
| **Boundedness** | Unbounded (all profiles); 14 currently |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI evidence: 14 profiles confirmed) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_c2257b50, t_4d983898 |
| **Caveat** | `spawnable` distinguishes `dispatcher_eligible` (predicate-level) from `end_to_end_observed` (4 profiles only). `effective_toolsets` uses runtime resolved values, not legacy top-level `toolsets:` field. |

---

#### `get_profile`

| Field | Value |
|-------|-------|
| **Domain** | Profiles / Skills |
| **Purpose** | Get detailed metadata for a single profile |
| **Inputs** | `{ profile: string }` |
| **Outputs** | `{ name, description, description_auto, model_provider, skill_count, local_skill_count, effective_toolsets, spawnable, evidence_marker }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `hermes profile list --json`) |
| **V4 proposed contract** | `get_profile` |
| **Primitive** | `hermes_cli.profiles.read_profile_meta()` + skill/toolset resolution |
| **Validation** | `profile` must exist in `list_profiles` |
| **Errors** | `PROFILE_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_c2257b50, t_4d983898 |

---

#### `list_skills`

| Field | Value |
|-------|-------|
| **Domain** | Profiles / Skills |
| **Purpose** | List all enabled skills for a profile, grouped by origin |
| **Inputs** | `{ profile?: string }` (defaults to default profile) |
| **Outputs** | `{ items: [{ name, description, origin, requires_toolsets, profiles }], total, by_origin: { builtin, local, hub } }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `hermes skills list --enabled-only`) |
| **V4 proposed contract** | `list_skills` |
| **Primitive** | `hermes skills list --enabled-only` (resolved via `_find_all_skills()`) |
| **Validation** | Profile must exist if specified |
| **Errors** | `PROFILE_NOT_FOUND`, `INTERNAL_ERROR` |
| **Boundedness** | 53 skills on default (39 builtin, 14 local, 0 hub) |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_2d78d03f, t_4d983898 |
| **CRITICAL CONSTRAINT** | V4 skill queries MUST use `skills list` or `skill_view`, never `hermes skills inspect` — inspect is hub-only and cannot resolve builtin/local skills (P0-4). |

---

#### `validate_profile_skills`

| Field | Value |
|-------|-------|
| **Domain** | Profiles / Skills |
| **Purpose** | Check whether a profile has all required skills for a given task spec |
| **Inputs** | `{ profile: string, required_skills: string[] }` |
| **Outputs** | `{ valid: boolean, missing: string[], present: string[] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `validate_profile_skills` |
| **Primitive** | `_find_all_skills()` + set intersection |
| **Validation** | Profile must exist; required_skills must be non-empty |
| **Errors** | `PROFILE_NOT_FOUND` |
| **Boundedness** | Bounded by skill count (53) |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_2d78d03f, t_4d983898 |
| **Caveat** | P0-5: Force-load pattern (sdlc-review) must be documented as union semantics — creation skills preserved, force-load appends at dispatch time. |

---

#### `validate_dispatch_requirements`

| Field | Value |
|-------|-------|
| **Domain** | Profiles / Skills |
| **Purpose** | Pre-flight check: can this task be dispatched to this profile? |
| **Inputs** | `{ task_id: string, profile?: string }` |
| **Outputs** | `{ dispatchable: boolean, reasons: string[], profile_exists: boolean, skills_valid: boolean, toolset_available: boolean }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `validate_dispatch_requirements` |
| **Primitive** | `profile_exists()` + skill resolution + toolset resolution |
| **Validation** | Task must exist; profile must exist |
| **Errors** | `TASK_NOT_FOUND`, `PROFILE_NOT_FOUND` |
| **Boundedness** | Single check |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_4d983898 |
| **Caveat** | Combines the three dispatcher gates. Not P0 in isolation — the dispatcher already validates these at dispatch time. Included in P0 for completeness of the profile/skills discovery surface. |

---

### P0.2 Task CRUD

#### `create_task`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Create a new Kanban task |
| **Inputs** | `{ title, body?, assignee?, priority?, parent_ids?, tenant?, idempotency_key?, workspace_kind?, workspace_path?, skills?, model?, provider?, goal_mode?, goal_max_turns?, max_runtime_seconds?, initial_status?, project?, triage? }` |
| **Outputs** | `{ created, idempotent_replay, task_id, board, title, status, assignee, priority, parent_ids, child_ids, created_by, created_at }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | `CreateTaskInput` (schemas.py:145-157) — subset of canonical args |
| **V4 proposed contract** | `create_task` |
| **Primitive** | `kanban_db.create_task()` via `HermesCreateAdapter` |
| **Validation** | title required (1-512 chars); parent_ids verified to exist; assignee verified via `profile_exists()`; idempotency_key prevents duplicate creation; workspace_kind must be scratch/dir/worktree |
| **Errors** | `VALIDATION_ERROR`, `BOARD_NOT_FOUND`, `TASK_NOT_FOUND` (parent), `PROFILE_NOT_FOUND` (assignee), `IDEMPOTENCY_CONFLICT` |
| **Boundedness** | Single creation |
| **Idempotency** | Idempotent with `idempotency_key` |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |
| **Caveat** | V4 extends current MCP schema with `skills`, `model`, `provider`, `goal_mode`, `workspace_kind`, `workspace_path`. `skills` field preserved in order; force-load appends at dispatch time (P0-5). |

---

#### `get_task`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Get full task detail including body, parents, children, runs, attachments |
| **Inputs** | `{ task_id: string }` |
| **Outputs** | `TaskDetail` (schemas.py:255-267) |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `get_task` |
| **Primitive** | `kanban_db.get_task()` + `parent_ids()` + `child_ids()` + `list_runs()` + `list_attachments()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5, t_ad6925aa |

---

#### `list_tasks`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | List tasks with filtering and pagination |
| **Inputs** | `{ status?, assignee?, tenant?, session_id?, include_archived?, limit?, order_by? }` |
| **Outputs** | `TaskListView` (schemas.py:249-253) |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `list_tasks` |
| **Primitive** | `kanban_db.list_tasks()` |
| **Validation** | status must be valid TaskStatus enum; limit 1-100 |
| **Errors** | `VALIDATION_ERROR` |
| **Boundedness** | Paginated (max 100 per page) |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5, t_ad6925aa |

---

#### `edit_task`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Update mutable task fields |
| **Inputs** | `{ task_id, title?, body?, priority?, assignee?, status?, skills?, model?, provider? }` |
| **Outputs** | `TaskDetail` (updated) |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (CLI: `kanban edit`) |
| **V4 proposed contract** | `edit_task` |
| **Primitive** | `kanban_db.edit_task()` |
| **Validation** | Task must exist; status transitions must be valid; assignee verified via `profile_exists()` if changed |
| **Errors** | `TASK_NOT_FOUND`, `VALIDATION_ERROR`, `PROFILE_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent (field-level merge) |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |
| **Caveat** | Status transitions constrained by state machine: triage→todo→scheduled→ready→running→blocked→review→done→archived. V4 should expose transition validation. |

---

#### `complete_task`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Mark task done with summary and metadata |
| **Inputs** | `{ task_id, summary?, result?, metadata?, artifacts?, created_cards? }` |
| **Outputs** | `{ task_id, status: "done", completed_at }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `complete_task` |
| **Primitive** | `kanban_db.complete_task()` |
| **Validation** | Task must exist; created_cards verified to exist |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION`, `PHANTOM_CARD_REFERENCE` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

### P0.3 Workers / Runs / Inspect / Terminate

#### `list_active_workers`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | List currently running workers with heartbeat/claim info |
| **Inputs** | `{}` |
| **Outputs** | `{ items: [{ run_id, task_id, profile, worker_pid, started_at, last_heartbeat, claim_expiry, runtime_seconds }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (dashboard plugin API: `GET /api/plugins/kanban/workers/active`) |
| **V4 proposed contract** | `list_active_workers` |
| **Primitive** | Dashboard plugin API `GET /api/plugins/kanban/workers/active` (plugin_api.py:1551-1609) |
| **Validation** | None |
| **Errors** | `BACKEND_UNAVAILABLE` if dashboard plugin not mounted |
| **Boundedness** | Unbounded (all active workers) |
| **Idempotency** | Idempotent read |
| **Status** | ❓ NOT_PROVEN (dashboard plugin API live mount status) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_ad6925aa |
| **Caveat** | Requires Kanban dashboard plugin to be enabled/mounted. Live mount status is STILL_NOT_PROVEN. |

---

#### `get_run`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | Get run details for a specific attempt |
| **Inputs** | `{ run_id: integer }` |
| **Outputs** | `TaskRunRecord` (schemas.py:210-220) |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (dashboard plugin API: `GET /api/plugins/kanban/runs/{run_id}`) |
| **V4 proposed contract** | `get_run` |
| **Primitive** | Dashboard `GET /api/plugins/kanban/runs/{run_id}` (plugin_api.py:1612-1631) |
| **Validation** | Run must exist |
| **Errors** | `RUN_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ❓ NOT_PROVEN (dashboard plugin API) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_ad6925aa |

---

#### `inspect_run`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | Get live process inspection for a running worker |
| **Inputs** | `{ run_id: integer }` |
| **Outputs** | `{ alive, pid, cpu_percent, rss_bytes, vms_bytes, threads, fds, status, create_time, cmdline }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (dashboard plugin API: `GET /api/plugins/kanban/runs/{run_id}/inspect`) |
| **V4 proposed contract** | `inspect_run` |
| **Primitive** | Dashboard `GET /api/plugins/kanban/runs/{run_id}/inspect` (plugin_api.py:1634-1700, psutil) |
| **Validation** | Run must exist; PID must be recorded; psutil must be available |
| **Errors** | `RUN_NOT_FOUND`, `PROCESS_NOT_ALIVE`, `PSUTIL_UNAVAILABLE` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ❓ NOT_PROVEN (dashboard plugin API) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_ad6925aa |

---

#### `terminate_run`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | Terminate/reclaim a running worker |
| **Inputs** | `{ run_id: integer }` |
| **Outputs** | `{ ok, run_id, task_id }` |
| **Risk** | `ADMIN` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (dashboard plugin API: `POST /api/plugins/kanban/runs/{run_id}/terminate`) |
| **V4 proposed contract** | `terminate_run` |
| **Primitive** | Dashboard `POST /api/plugins/kanban/runs/{run_id}/terminate` (calls `reclaim_task()`) |
| **Validation** | Run must exist; run must be active |
| **Errors** | `RUN_NOT_FOUND`, `RUN_NOT_ACTIVE` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_ad6925aa |
| **Caveat** | Routes through `reclaim_task`. UNSAFE_TO_TEST for live behavior. |

---

### P0.4 Runtime / Build / Provenance

#### `get_build_info`

| Field | Value |
|-------|-------|
| **Domain** | Runtime |
| **Purpose** | Get build version, SHA, install info |
| **Inputs** | `{}` |
| **Outputs** | `{ hermes_version, upstream_sha, local_head, install_dir, install_method, python_version, openai_sdk_version, executable }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `hermes version`) |
| **V4 proposed contract** | `get_build_info` |
| **Primitive** | `hermes version` output parsing |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_ad6925aa, t_4d983898 |

---

#### `gateway_status`

| Field | Value |
|-------|-------|
| **Domain** | Runtime |
| **Purpose** | Get gateway lifecycle status |
| **Inputs** | `{}` |
| **Outputs** | `{ gateway_running, pid, profile, dispatch_enabled, connector_label, api_server_port, uptime }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `hermes gateway status`) |
| **V4 proposed contract** | `gateway_status` |
| **Primitive** | `hermes gateway status` + runtime introspection |
| **Validation** | None |
| **Errors** | `BACKEND_UNAVAILABLE` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_ad6925aa, t_4d983898 |

---

### P0.5 Safe Remote Attachment

#### `attach_file`

| Field | Value |
|-------|-------|
| **Domain** | Attachments |
| **Purpose** | Upload a file to a task (base64 inline for remote clients) |
| **Inputs** | `{ task_id, content_base64, filename, content_type? }` |
| **Outputs** | `{ filename, content_type, size, created_at }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | `attach(local_path=...)` — PARTIAL: local_path only, no content_base64 |
| **V4 proposed contract** | `attach_file` |
| **Primitive** | `kanban_db.store_attachment_bytes()` |
| **Validation** | Task must exist; base64 decode must succeed; size ≤ 25MB; filename sanitized via `_safe_attachment_name()` |
| **Errors** | `TASK_NOT_FOUND`, `VALIDATION_ERROR` (bad base64), `SIZE_LIMIT_EXCEEDED`, `FILENAME_REJECTED` |
| **Boundedness** | Single upload |
| **Idempotency** | Not idempotent (file storage) |
| **Status** | ⚠️ DISPONIBLE CON ERRORES / INCONSISTENCIAS (MCP connector: local_path only, SERVER_LOCAL_BOUND) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_2499ad0a, t_4d983898 |
| **Caveat** | P0-1: Current MCP `attach(local_path=...)` is architecturally wrong for remote clients. V4 MUST add `content_base64` field. P0-2: Size cap must be unified to 25MB (agent=25MB, MCP connector default=10MB). P0-3: Deployed connector SHA is STILL_NOT_PROVEN. |

---

#### `list_attachments`

| Field | Value |
|-------|-------|
| **Domain** | Attachments |
| **Purpose** | List attachments for a task |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ items: [{ filename, content_type, size, uploaded_by, created_at }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban attachments`) |
| **V4 proposed contract** | `list_attachments` |
| **Primitive** | `kanban_db.list_attachments()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Paginated (per-task) |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

### P0.6 Core Board/Task Reads & Writes (Orchestration)

#### `add_comment`

| Field | Value |
|-------|-------|
| **Domain** | Comments |
| **Purpose** | Add a comment to a task |
| **Inputs** | `{ task_id, body }` |
| **Outputs** | `AddCommentResult` (schemas.py:125-132) |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `add_comment` |
| **Primitive** | `kanban_db.add_comment()` |
| **Validation** | Task must exist; body 1-16000 chars |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single creation |
| **Idempotency** | Not idempotent |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `get_activity`

| Field | Value |
|-------|-------|
| **Domain** | Comments |
| **Purpose** | Get events, comments, runs, and log for a task |
| **Inputs** | `{ task_id, max_items?, log_bytes? }` |
| **Outputs** | `ActivityView` (schemas.py:297-304) |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban log`) |
| **V4 proposed contract** | `get_activity` |
| **Primitive** | `kanban_db.list_events()` + `list_comments()` + `list_runs()` + `get_task_log()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Paginated (max_items, log_bytes) |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated: `kanban log`, `kanban runs`) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ad6925aa |

---

#### `get_task_graph`

| Field | Value |
|-------|-------|
| **Domain** | Task Graph |
| **Purpose** | Get parent/child dependency graph for a task |
| **Inputs** | `{ task_id, depth?, max_nodes? }` |
| **Outputs** | `TaskGraphView` (schemas.py:282-287) |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `get_task_graph` |
| **Primitive** | `kanban_db.parent_ids()` + `kanban_db.child_ids()` recursive |
| **Validation** | Task must exist; depth 0-8; max_nodes 1-500 |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Bounded by depth/max_nodes |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `link_tasks`

| Field | Value |
|-------|-------|
| **Domain** | Task Graph |
| **Purpose** | Add parent→child dependency edge |
| **Inputs** | `{ parent_id, child_id }` |
| **Outputs** | `{ linked: boolean, parent_id, child_id }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `link_tasks` |
| **Primitive** | `kanban_db.link_tasks()` |
| **Validation** | Both tasks must exist; no cycles allowed; no self-links |
| **Errors** | `TASK_NOT_FOUND`, `CYCLE_DETECTED`, `SELF_LINK` |
| **Boundedness** | Single mutation |
| **Idempotency** | Idempotent (re-link is no-op) |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `kanban_assignees`

| Field | Value |
|-------|-------|
| **Domain** | Profiles |
| **Purpose** | List dispatcher-eligible profiles |
| **Inputs** | `{}` |
| **Outputs** | `{ items: [{ name, description, model_provider, skill_count }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban assignees`) |
| **V4 proposed contract** | `kanban_assignees` |
| **Primitive** | `kanban_db.list_assignees()` |
| **Validation** | None |
| **Errors** | None |
| **Boundedness** | Unbounded (all eligible profiles) |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_c2257b50 |

---

#### `kanban_runs`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | Get task run history |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ items: [{ run_id, profile, status, started_at, ended_at, error }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban runs`) |
| **V4 proposed contract** | `kanban_runs` |
| **Primitive** | `kanban_db.get_runs()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Bounded by run count |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ad6925aa |

---

#### `kanban_reclaim`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | Reclaim stuck/running task |
| **Inputs** | `{ task_id, force? }` |
| **Outputs** | `{ reclaimed: boolean, task_id, old_status }` |
| **Risk** | `ADMIN` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (CLI: `kanban reclaim`) |
| **V4 proposed contract** | `kanban_reclaim` |
| **Primitive** | `kanban_db.reclaim_task()` |
| **Validation** | Task must exist; task must be running/blocked; force overrides |
| **Errors** | `TASK_NOT_FOUND`, `TASK_NOT_RECLAIMABLE` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ad6925aa |
| **Caveat** | Destructive operation. UNSAFE_TO_TEST for live behavior. |

---

#### `kanban_request_review`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Move task to review column |
| **Inputs** | `{ task_id, summary, metadata?, reviewer? }` |
| **Outputs** | `{ task_id, status: "review" }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (CLI: `kanban request-review`) |
| **V4 proposed contract** | `kanban_request_review` |
| **Primitive** | `kanban_db.request_review()` |
| **Validation** | Task must exist; task must be running |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_2d78d03f |
| **Caveat** | Force-loads `sdlc-review` at dispatch time (P0-5). Production-critical pattern must be preserved. |

---

#### `kanban_list_boards`

| Field | Value |
|-------|-------|
| **Domain** | Boards |
| **Purpose** | List all boards |
| **Inputs** | `{}` |
| **Outputs** | `{ items: [{ slug, name, task_count, active_workers }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban boards`) |
| **V4 proposed contract** | `kanban_list_boards` |
| **Primitive** | `kanban_db.list_boards()` |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Boundedness** | Unbounded (all boards) |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated) |
| **Priority** | P0 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ef94f514 |

---

### P0.7 Auth / Contract Evidence

#### P0 Blocker Summary

| ID | Title | Severity | Evidence |
|----|-------|----------|----------|
| P0-1 | Add `content_base64` to MCP connector AttachInput | BLOCKING | t_2499ad0a |
| P0-2 | Unify attachment size cap (25MB agent vs 10MB MCP) | HIGH | t_2499ad0a |
| P0-3 | Pin deployed connector SHA | MEDIUM | t_2499ad0a |
| P0-4 | V4 skill queries: use `skills list` or `skill_view`, never `inspect` | MEDIUM | t_2d78d03f |
| P0-5 | Preserve sdlc-review force-load pattern | PRODUCTION_CRITICAL | t_2d78d03f |

These five synthesis P0 blockers are release blockers, not the whole P0. The full P0 feature scope is the tools listed above.

---

## P1 — Important for V4, Non-Blocking

### P1.1 Effective Profile Tools / Toolsets

#### `get_profile_tools`

| Field | Value |
|-------|-------|
| **Domain** | Profiles / Tools |
| **Purpose** | Get effective toolset for a profile (runtime resolved) |
| **Inputs** | `{ profile: string }` |
| **Outputs** | `{ profile, effective_toolsets: [{ name, tool_count, tools: string[] }], legacy_toolsets, mismatch }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `get_profile_tools` |
| **Primitive** | `_get_platform_tools()` + profile toolset resolution |
| **Validation** | Profile must exist |
| **Errors** | `PROFILE_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_c2257b50 |
| **Caveat** | P1-1: Use runtime effective CLI toolsets for profile routing. Legacy toolsets field produces broader surface than expected. |

---

### P1.2 Kanban Config Effective State

#### `get_kanban_config`

| Field | Value |
|-------|-------|
| **Domain** | Config |
| **Purpose** | Get effective Kanban configuration |
| **Inputs** | `{}` |
| **Outputs** | `{ dispatch_in_gateway, dispatch_interval_seconds, dispatch_stale_timeout_seconds, auto_decompose, max_in_progress, kanban_home, ... }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `get_kanban_config` |
| **Primitive** | `hermes config get kanban.*` + config_defaults.py |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_ef94f514 |
| **Caveat** | Managed overlay existence is STILL_NOT_PROVEN. Active profile/default source values resolved. |

---

### P1.3 Gateway / Dispatcher Observability

#### `get_dispatcher_status`

| Field | Value |
|-------|-------|
| **Domain** | Runtime |
| **Purpose** | Get dispatcher state: lock, tick, zombie count, auto-decompose |
| **Inputs** | `{}` |
| **Outputs** | `{ lock_held, lock_owner_pid, last_tick, tick_interval, zombies_reaped, auto_decompose_enabled, boards_dispatched }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban diagnostics`) |
| **V4 proposed contract** | `get_dispatcher_status` |
| **Primitive** | `kanban_db.diagnostics()` + lock file inspection |
| **Validation** | None |
| **Errors** | `BACKEND_UNAVAILABLE` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated: `kanban diagnostics`) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ad6925aa |

---

### P1.4 Notifications / Events

#### `subscribe_notifications`

| Field | Value |
|-------|-------|
| **Domain** | Notifications |
| **Purpose** | Subscribe to board/task notifications |
| **Inputs** | `{ channel, filter? }` |
| **Outputs** | `{ subscription_id, channel, filter }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `subscribe_notifications` |
| **Primitive** | `kanban_db.subscribe()` |
| **Validation** | channel must be valid |
| **Errors** | `VALIDATION_ERROR` |
| **Boundedness** | Single creation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P1 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |

---

#### `poll_notifications`

| Field | Value |
|-------|-------|
| **Domain** | Notifications |
| **Purpose** | Poll for new notifications since last read |
| **Inputs** | `{ subscription_id, max_items? }` |
| **Outputs** | `{ items: [{ event_type, task_id, timestamp, payload }], has_more }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `poll_notifications` |
| **Primitive** | `kanban_db.list_subscriptions()` + event cursor |
| **Validation** | Subscription must exist |
| **Errors** | `SUBSCRIPTION_NOT_FOUND` |
| **Boundedness** | Paginated |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P1 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |

---

### P1.5 Spawnability / Readiness

#### `get_spawn_status`

| Field | Value |
|-------|-------|
| **Domain** | Workers |
| **Purpose** | Get spawn readiness for a profile |
| **Inputs** | `{ profile }` |
| **Outputs** | `{ profile, dispatcher_eligible, end_to_end_observed, toolset_available, skills_resolvable, last_spawn_task, last_spawn_time }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `get_spawn_status` |
| **Primitive** | `profile_exists()` + toolset resolution + spawn history |
| **Validation** | Profile must exist |
| **Errors** | `PROFILE_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_c2257b50 |
| **Caveat** | P1-2: Represent spawnability as `dispatcher_eligible` vs `end_to_end_observed`. Only 4 profiles have observed spawn. |

---

### P1.6 Deeper Provenance / Diagnostics

#### `get_run_log`

| Field | Value |
|-------|-------|
| **Domain** | Workers / Runs |
| **Purpose** | Get log output for a specific run |
| **Inputs** | `{ run_id, offset?, limit? }` |
| **Outputs** | `{ log: string, truncated: boolean, total_bytes }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban log --tail`) |
| **V4 proposed contract** | `get_run_log` |
| **Primitive** | `kanban_db.get_task_log()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Paginated (offset/limit) |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ad6925aa |

---

### P1.7 Additional P1 Tools

#### `get_attachment`

| Field | Value |
|-------|-------|
| **Domain** | Attachments |
| **Purpose** | Get attachment content (base64 encoded) |
| **Inputs** | `{ task_id, filename }` |
| **Outputs** | `{ filename, content_type, size, content_base64 }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `get_attachment` |
| **Primitive** | `kanban_db.get_attachment_bytes()` |
| **Validation** | Task and attachment must exist |
| **Errors** | `TASK_NOT_FOUND`, `ATTACHMENT_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `block_task`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Set task to blocked with reason |
| **Inputs** | `{ task_id, reason, kind? }` |
| **Outputs** | `{ task_id, status: "blocked", block_kind, reason }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `block_task` |
| **Primitive** | `kanban_db.block_task()` |
| **Validation** | Task must exist; reason required |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `unblock_task`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Remove block from task |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ task_id, status }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `unblock_task` |
| **Primitive** | `kanban_db.unblock_task()` |
| **Validation** | Task must exist; task must be blocked |
| **Errors** | `TASK_NOT_FOUND`, `TASK_NOT_BLOCKED` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `promote_task`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Advance task to next status |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ task_id, old_status, new_status }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `promote_task` |
| **Primitive** | `kanban_db.promote_task()` |
| **Validation** | Task must exist; transition must be valid |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `request_changes`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Return review to implementer |
| **Inputs** | `{ task_id, reason }` |
| **Outputs** | `{ task_id, status }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `request_changes` |
| **Primitive** | `kanban_db.request_changes()` |
| **Validation** | Task must exist; task must be in review |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_edit`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Edit task fields |
| **Inputs** | `{ task_id, title?, body?, priority?, assignee? }` |
| **Outputs** | `TaskDetail` (updated) |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (CLI: `kanban edit`) |
| **V4 proposed contract** | `kanban_edit` |
| **Primitive** | `kanban_db.edit_task()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND`, `VALIDATION_ERROR` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_comment`

| Field | Value |
|-------|-------|
| **Domain** | Comments |
| **Purpose** | Add comment to task |
| **Inputs** | `{ task_id, body }` |
| **Outputs** | `AddCommentResult` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `kanban_comment` |
| **Primitive** | `kanban_db.add_comment()` |
| **Validation** | Task must exist; body 1-16000 chars |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single creation |
| **Idempotency** | Not idempotent |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `kanban_link`

| Field | Value |
|-------|-------|
| **Domain** | Task Graph |
| **Purpose** | Add parent→child dependency |
| **Inputs** | `{ parent_id, child_id }` |
| **Outputs** | `{ linked: boolean }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `kanban_link` |
| **Primitive** | `kanban_db.link_tasks()` |
| **Validation** | Both tasks exist; no cycles; no self-links |
| **Errors** | `TASK_NOT_FOUND`, `CYCLE_DETECTED` |
| **Boundedness** | Single mutation |
| **Idempotency** | Idempotent (re-link is no-op) |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `kanban_claim`

| Field | Value |
|-------|-------|
| **Domain** | Workers |
| **Purpose** | Claim task for worker |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ claimed: boolean, task_id }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `kanban_claim` |
| **Primitive** | `kanban_db.claim_task()` |
| **Validation** | Task must exist; task must be ready |
| **Errors** | `TASK_NOT_FOUND`, `TASK_NOT_READY` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `kanban_heartbeat`

| Field | Value |
|-------|-------|
| **Domain** | Workers |
| **Purpose** | Send worker heartbeat |
| **Inputs** | `{ task_id, note? }` |
| **Outputs** | `{ ok: boolean, task_id }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | Registered (tool exists) |
| **V4 proposed contract** | `kanban_heartbeat` |
| **Primitive** | `kanban_db.heartbeat_claim()` |
| **Validation** | Task must exist; worker must hold claim |
| **Errors** | `TASK_NOT_FOUND`, `NOT_CLAIMED` |
| **Boundedness** | Single mutation |
| **Idempotency** | Idempotent (re-heartbeat is fine) |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP tool registered) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_stats`

| Field | Value |
|-------|-------|
| **Domain** | Observability |
| **Purpose** | Board statistics |
| **Inputs** | `{}` |
| **Outputs** | `{ total_tasks, by_status: {...}, active_workers, avg_runtime }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban stats`) |
| **V4 proposed contract** | `kanban_stats` |
| **Primitive** | `kanban_db.stats()` |
| **Validation** | None |
| **Errors** | None |
| **Boundedness** | Single aggregate |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ef94f514 |

---

#### `kanban_context`

| Field | Value |
|-------|-------|
| **Domain** | Workers |
| **Purpose** | Get task context for worker |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ task, parents, children, workspace, skills, profile }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban context`) |
| **V4 proposed contract** | `kanban_context` |
| **Primitive** | `kanban_db.get_context()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single item |
| **Idempotency** | Idempotent read |
| **Status** | ✅ DISPONIBLE Y VALIDADO (CLI validated) |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_tail`

| Field | Value |
|-------|-------|
| **Domain** | Observability |
| **Purpose** | Tail task log |
| **Inputs** | `{ task_id, lines?, follow? }` |
| **Outputs** | `{ log: string, truncated: boolean }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None (CLI: `kanban tail`) |
| **V4 proposed contract** | `kanban_tail` |
| **Primitive** | `kanban_db.tail_log()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Paginated |
| **Idempotency** | Idempotent read |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_dispatch`

| Field | Value |
|-------|-------|
| **Domain** | Runtime |
| **Purpose** | Single dispatch tick |
| **Inputs** | `{ board? }` |
| **Outputs** | `{ dispatched: number, reapplied: number, errors: string[] }` |
| **Risk** | `ADMIN` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (CLI: `kanban dispatch`) |
| **V4 proposed contract** | `kanban_dispatch` |
| **Primitive** | `kanban_db.dispatch_once()` |
| **Validation** | Board must exist; dispatcher lock must be available |
| **Errors** | `DISPATCH_LOCK_HELD`, `BOARD_NOT_FOUND` |
| **Boundedness** | Single tick |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5, t_ad6925aa |
| **Caveat** | Embedded in gateway. Standalone daemon is DEPRECATED. |

---

#### `kanban_decompose`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Auto-decompose triage task |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ decomposed: boolean, child_count: number }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_decompose` |
| **Primitive** | `kanban_db.decompose_task()` |
| **Validation** | Task must exist; task must be in triage |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_repair`

| Field | Value |
|-------|-------|
| **Domain** | Maintenance |
| **Purpose** | Repair board inconsistencies |
| **Inputs** | `{}` |
| **Outputs** | `{ repaired: number, issues: string[] }` |
| **Risk** | `ADMIN` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None (CLI: `kanban repair`) |
| **V4 proposed contract** | `kanban_repair` |
| **Primitive** | `kanban_db.repair()` |
| **Validation** | Board must exist |
| **Errors** | `INTERNAL_ERROR` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |
| **Caveat** | Destructive operation. Requires explicit contract to prevent unguarded use. |

---

#### `kanban_swarm`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Create multiple tasks (orchestrator fan-out) |
| **Inputs** | `{ parent, count, assignee, title_prefix? }` |
| **Outputs** | `{ created: [{ task_id, title }] }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_swarm` |
| **Primitive** | `kanban_db.swarm_create()` |
| **Validation** | Parent must exist; assignee must be valid |
| **Errors** | `TASK_NOT_FOUND`, `PROFILE_NOT_FOUND` |
| **Boundedness** | Bounded by count |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P1 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

## P2 — Nice to Have for V4

#### `kanban_set_model`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Override model/provider for a task |
| **Inputs** | `{ task_id, model?, provider?, reasoning? }` |
| **Outputs** | `{ task_id, model, provider }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_set_model` |
| **Primitive** | `kanban_db.set_task_model()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P2 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_reassign`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Reassign to different profile |
| **Inputs** | `{ task_id, assignee }` |
| **Outputs** | `{ task_id, assignee }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_reassign` |
| **Primitive** | `kanban_db.reassign_task()` |
| **Validation** | Task must exist; assignee must be valid |
| **Errors** | `TASK_NOT_FOUND`, `PROFILE_NOT_FOUND` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P2 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_unlink`

| Field | Value |
|-------|-------|
| **Domain** | Task Graph |
| **Purpose** | Remove dependency edge |
| **Inputs** | `{ parent_id, child_id }` |
| **Outputs** | `{ unlinked: boolean }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | Validated via MCP E2E |
| **V4 proposed contract** | `kanban_unlink` |
| **Primitive** | `kanban_db.unlink_tasks()` |
| **Validation** | Both tasks must exist; edge must exist |
| **Errors** | `TASK_NOT_FOUND`, `EDGE_NOT_FOUND` |
| **Boundedness** | Single mutation |
| **Idempotency** | Idempotent (re-unlink is no-op) |
| **Status** | ✅ DISPONIBLE Y VALIDADO (MCP E2E validated) |
| **Priority** | P2 |
| **Target** | V4 |
| **Evidence** | board QA evidence, t_59a2a2f5 |

---

#### `kanban_remove_attachment`

| Field | Value |
|-------|-------|
| **Domain** | Attachments |
| **Purpose** | Remove an attachment from a task |
| **Inputs** | `{ task_id, filename }` |
| **Outputs** | `{ removed: boolean }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_remove_attachment` |
| **Primitive** | `kanban_db.remove_attachment()` |
| **Validation** | Task and attachment must exist |
| **Errors** | `TASK_NOT_FOUND`, `ATTACHMENT_NOT_FOUND` |
| **Boundedness** | Single mutation |
| **Idempotency** | Idempotent (re-remove is no-op) |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P2 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_schedule`

| Field | Value |
|-------|-------|
| **Domain** | Task CRUD |
| **Purpose** | Schedule future task |
| **Inputs** | `{ at?, cron?, title, body? }` |
| **Outputs** | `{ task_id, scheduled_at }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_schedule` |
| **Primitive** | `kanban_db.schedule_task()` |
| **Validation** | title required; at or cron must be valid |
| **Errors** | `VALIDATION_ERROR` |
| **Boundedness** | Single creation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P2 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_archive`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Archive completed task |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ archived: boolean }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_archive` |
| **Primitive** | `kanban_db.archive_task()` |
| **Validation** | Task must exist; task must be done |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P2 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_reopen_review`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Reopen closed review |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ task_id, status }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_reopen_review` |
| **Primitive** | `kanban_db.reopen_review()` |
| **Validation** | Task must exist; task must be in review/done |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️ PLANIFICADO V4 |
| **Priority** | P2 |
| **Target** | V4 |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_specify`

| Field | Value |
|-------|-------|
| **Domain** | Task Lifecycle |
| **Purpose** | Add acceptance criteria |
| **Inputs** | `{ task_id, criteria }` |
| **Outputs** | `{ task_id, criteria_count }` |
| **Risk** | `WRITE` |
| **Current scope** | `hermes:create` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_specify` |
| **Primitive** | `kanban_db.specify()` |
| **Validation** | Task must exist; criteria non-empty |
| **Errors** | `TASK_NOT_FOUND` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P2 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_watch`

| Field | Value |
|-------|-------|
| **Domain** | Observability |
| **Purpose** | Watch board for changes |
| **Inputs** | `{ interval? }` |
| **Outputs** | `{ events: [{ type, task_id, timestamp }] }` |
| **Risk** | `READ` |
| **Current scope** | `hermes:read` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_watch` |
| **Primitive** | `kanban_db.watch()` |
| **Validation** | None |
| **Errors** | None |
| **Boundedness** | Streaming (infinite) |
| **Idempotency** | N/A |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P2 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |

---

#### `kanban_gc`

| Field | Value |
|-------|-------|
| **Domain** | Maintenance |
| **Purpose** | Garbage collect old data |
| **Inputs** | `{ days? }` |
| **Outputs** | `{ collected: number }` |
| **Risk** | `ADMIN` |
| **Current scope** | `hermes:manage` |
| **Current live MCP tool** | None |
| **V4 proposed contract** | `kanban_gc` |
| **Primitive** | `kanban_db.gc()` |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Boundedness** | Single mutation |
| **Idempotency** | Not idempotent |
| **Status** | 🗓️+ PLANIFICADO V4.x |
| **Priority** | P2 |
| **Target** | V4.x |
| **Evidence** | t_59a2a2f5 |
| **Caveat** | Destructive operation. Requires explicit narrowly-scoped contract. |

---

## P3 — Deferred

No P3 tools defined for V4 MCP surface. P3 items from CLI matrix (proxy, lsp, skin, console, pets, journey, learning, gui, prompt-size, etc.) are not relevant to MCP control plane.

---

## DO_NOT_EXPOSE — Risk-Based Exclusions

These tools must NOT be exposed via MCP. Classification is risk-based: generic shell/argv/raw command, unguarded destructive repair/gc, arbitrary kill/terminate, secrets/auth/update/uninstall/global config mutation absent an explicit narrowly-scoped contract, unsafe platform operations.

| Tool | Risk Category | Rationale | Evidence |
|------|--------------|-----------|----------|
| `kanban daemon` | Destructive (deprecated) | Standalone dispatch daemon; DEPRECATED in favor of embedded gateway dispatcher | t_59a2a2f5, t_ad6925aa |
| Raw `terminal` / `process` | Generic shell/argv | Unrestricted shell execution; no MCP-safe contract exists | t_5caf4595 |
| `delegate_task` | Arbitrary kill/terminate | Spawns subagents with full profile privileges; no scoped contract | t_5caf4595 |
| `secrets` | Secrets/auth mutation | Credential management; no narrowly-scoped MCP contract | t_59a2a2f5 |
| `auth` / `login` / `logout` | Auth mutation | Authentication state changes; no MCP-safe contract | t_59a2a2f5 |
| `update` | System mutation | Self-update; no MCP-safe contract | t_59a2a2f5 |
| `uninstall` | Destructive | Uninstall operation; no MCP-safe contract | t_59a2a2f5 |
| `config set` (global) | Global config mutation | System-wide config changes; no narrowly-scoped MCP contract | t_59a2a2f5 |
| `kanban repair` (unguarded) | Unguarded destructive | Board repair without confirmation; P1 version exists with explicit contract | t_59a2a2f5 |
| `kanban gc` (unguarded) | Unguarded destructive | Garbage collection without confirmation; P2 version exists with explicit contract | t_59a2a2f5 |
| `computer_use` | Unsafe platform | Direct platform control; no MCP-safe contract | t_5caf4595 |
| `pause` / `resume` (global) | Global control | ESTOP sentinel; board-local pause does not exist | t_ef94f514 |

**Note:** DO_NOT_EXPOSE is risk-based classification, not a claim that these tools are unproven. Research questions about unknown behavior are NOT placed here — they belong in NOT_PROVEN.

---

## NOT_PROVEN — Behavioral Unknowns

These items exist in source/CLI but behavior was not exercised. They are NOT placed in DO_NOT_EXPOSE.

| Item | Classification | Notes |
|------|---------------|-------|
| Dashboard plugin API live mount/auth | STILL_NOT_PROVEN | No live HTTP request; port-conflict warning observed |
| Deployed connector SHA | STILL_NOT_PROVEN | Local master stale; live schema shows attach tool present |
| Live `/kanban` connector delivery/ACL | UNSAFE_TO_TEST | Production slash invocation intentionally not sent |
| Live Kanban terminate/reclaim behavior | UNSAFE_TO_TEST | Would mutate worker/task state |
| Live heartbeat, stale, crash, timeout behavior | UNSAFE_TO_TEST | Would mutate state or require induced failure |
| Provider credentials/model quota | STILL_NOT_PROVEN | Secrets not inspected; no provider call made |
| Native `/v1/runs` listener auth | STILL_NOT_PROVEN | Routes exist in source; no live HTTP request |
| MCP protocol support for base64 file content | NOT_PROVEN | Connector schema lacks field; protocol not separately inspected |
| ChatGPT client ability to send `content_base64` | NOT_PROVEN | Depends on future connector schema/client behavior |

---

## MCP Topology Note

**Decision:** Single MCP server with internally privilege-separated adapters (ADR t_484d4ab0).

**Rejected for V4:**
- Separate companion MCP for profiles/skills (rejected: tightly coupled with task creation)
- Separate companion MCP for runtime/workers (rejected: fragments task lifecycle view)
- Serverless/Lambda MCP (rejected: breaks persistent SQLite + dispatcher lock invariants)

Future optional separation is recorded as ADR follow-up only.

---

## Appendix A: Scope Migration Mapping

| Current Scope | → Proposed Scopes |
|---------------|-------------------|
| `hermes:read` | `hermes:task:read`, `hermes:attachment:read`, `hermes:profile:read`, `hermes:worker:read`, `hermes:gateway:read`, `hermes:tool:read`, `hermes:config:read`, `hermes:board:read`, `hermes:notification:read` |
| `hermes:create` | `hermes:task:create`, `hermes:comment:create`, `hermes:attachment:create`, `hermes:notification:create` |
| `hermes:manage` | `hermes:task:write`, `hermes:attachment:delete`, `hermes:worker:terminate`, `hermes:config:write` |
| `hermes:board:create` | `hermes:board:create` (unchanged) |

**Note:** V4 tools use CURRENT scope names. Any implementation adopting PROPOSED scopes MUST provide backward compatibility via scope aggregation.

---

## Appendix B: Summary Counts

### By Priority

| Priority | Count | Statuses |
|----------|-------|----------|
| P0 | 19 | ✅ DISPONIBLE Y VALIDADO: 11, ⚠️ DISPONIBLE CON ERRORES: 1, 🗓️ PLANIFICADO V4: 6, ❓ NOT_PROVEN: 1 |
| P1 | 21 | ✅ DISPONIBLE Y VALIDADO: 10, 🗓️ PLANIFICADO V4: 11 |
| P2 | 10 | ✅ DISPONIBLE Y VALIDADO: 1, 🗓️ PLANIFICADO V4: 5, 🗓️+ PLANIFICADO V4.x: 4 |
| P3 | 0 | — |
| DO_NOT_EXPOSE | 12 | Risk-based exclusions |
| **Total** | **62** | |

### By Status

| Status | Count |
|--------|-------|
| ✅ DISPONIBLE Y VALIDADO | 22 |
| ⚠️ DISPONIBLE CON ERRORES / INCONSISTENCIAS | 1 |
| 🗓️ PLANIFICADO V4 | 22 |
| 🗓️+ PLANIFICADO V4.x | 4 |
| ❓ NOT_PROVEN | 1 |
| DO_NOT_EXPOSE | 12 |

---

*End of V4 MCP Tool Catalog Draft*
