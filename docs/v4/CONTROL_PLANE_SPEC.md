# V4 Control Plane Spec — Canonical V4 Documentation

**Date:** 2026-08-19
**Author:** software-architect (t_f96c8f07) (integrated by github-steward task t_70297725)
**Evidence baseline:** Hermes v0.20.2, source HEAD 39cfd1ab41, board `hermes-chatgpt-mcp`
**Synthesis source:** t_2d568471 and seven parent leaves
**Status:** CANONICAL — integrated into docs/v4/ as part of V4 documentation
**Supersedes:** t_f96c8f07
**Artifact lifecycle issue:** artifact lifecycle issue: post_complete_workspace_changes_not_durable

---

## 0. Scope and conventions

This spec defines the V4 tool contract for the Hermes ChatGPT MCP control plane.
It covers every tool that should be exposed to a remote ChatGPT client via MCP
JSON-RPC, with rationale for inclusion/exclusion based on local evidence.

**Convention abbreviations:**
- `READ` = read-only operation, no state mutation
- `WRITE` = state-mutating operation
- `PRIMITIVE` = the underlying Hermes source function or API surface
- `P0/P1/P2/P3` = priority tier (P0 = blocking for release)
- `DO_NOT_EXPOSE` = intentionally not exposed to ChatGPT MCP

**Evidence preserved:**
- All `NOT_PROVEN` items from synthesis are explicitly tagged
- Claims are bound to local v0.20.2 / HEAD 39cfd1ab41
- No runtime behavioral claims beyond source inspection

---

## 1. Tool inventory

### 1.1 Profiles / Skills introspection

#### `list_profiles`

| Field | Value |
|-------|-------|
| **Purpose** | List all installed Hermes profiles with metadata |
| **Inputs** | `{}` (empty; board scope implicit from session) |
| **Outputs** | `{ items: [{ name, description, model_provider, skill_count, effective_toolsets, disponible }] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes_cli.profiles.list_profiles()` + `hermes_cli.tools_config._get_platform_tools()` |
| **Validation** | None (pure read) |
| **Errors** | `BOARD_NOT_FOUND` if board invalid; `INTERNAL_ERROR` if profile registry unavailable |
| **Priority** | `P0` |
| **Target** | V4 |

**Rationale:** Profile discovery is the entry point for all worker routing. Without it, a ChatGPT client cannot determine which profiles exist, what models they use, or what skills they have. Evidence: 14 profiles confirmed via `hermes profile list` (t_c2257b50). Descriptions, model/provider, and skill counts are all RESOLVED_LOCALLY.

**Notes:**
- `spawnable` field distinguishes `dispatcher_eligible` (predicate-level) from `end_to_end_observed` (only investigator/ profile-architect/operator/software-architect observed)
- `effective_toolsets` uses runtime resolved values, not legacy top-level `toolsets:` field (P1-1 recommendation)

---

#### `get_profile`

| Field | Value |
|-------|-------|
| **Purpose** | Get detailed metadata for a single profile |
| **Inputs** | `{ profile: string }` |
| **Outputs** | `{ name, description, description_auto, model_provider, skill_count, local_skill_count, effective_toolsets, spawnable, evidence_marker }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes_cli.profiles.read_profile_meta()` + skill/toolset resolution |
| **Validation** | `profile` must exist in `list_profiles` |
| **Errors** | `PROFILE_NOT_FOUND` if name unknown |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `list_skills`

| Field | Value |
|-------|-------|
| **Purpose** | List all enabled skills for a profile, grouped by origin |
| **Inputs** | `{ profile?: string }` (defaults to default profile) |
| **Outputs** | `{ items: [{ name, description, origin, requires_toolsets, profiles }], total, by_origin: { builtin, local, hub } }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes skills list --enabled-only` (resolved via `_find_all_skills()`) |
| **Validation** | Profile must exist if specified |
| **Errors** | `PROFILE_NOT_FOUND`, `INTERNAL_ERROR` |
| **Priority** | `P0` |
| **Target** | V4 |

**CRITICAL CONSTRAINT:** V4 skill queries MUST use `skills list` or `skill_view`, never `hermes skills inspect` — inspect is hub-only and cannot resolve builtin/local skills (P0-4). Evidence: t_2d78d03f, 53 enabled skills on default (39 builtin, 14 local, 0 hub).

---

#### `get_skill`

| Field | Value |
|-------|-------|
| **Purpose** | Get full content/metadata for a specific skill |
| **Inputs** | `{ skill_name: string }` |
| **Outputs** | `{ name, content, origin, hash, frontmatter: { description, category, requires_toolsets, platforms, environments } }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `skill_view(name=...)` |
| **Validation** | Skill must exist |
| **Errors** | `SKILL_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `validate_profile_skills`

| Field | Value |
|-------|-------|
| **Purpose** | Check whether a profile has all required skills for a given task spec |
| **Inputs** | `{ profile: string, required_skills: string[] }` |
| **Outputs** | `{ valid: boolean, missing: string[], present: string[] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `_find_all_skills()` + set intersection |
| **Validation** | Profile must exist; required_skills must be non-empty |
| **Errors** | `PROFILE_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `validate_dispatch_requirements`

| Field | Value |
|-------|-------|
| **Purpose** | Pre-flight check: can this task be dispatched to this profile? |
| **Inputs** | `{ task_id: string, profile?: string }` |
| **Outputs** | `{ dispatchable: boolean, reasons: string[], profile_exists: boolean, skills_valid: boolean, toolset_available: boolean }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `profile_exists()` + skill resolution + toolset resolution |
| **Validation** | Task must exist; profile must exist |
| **Errors** | `TASK_NOT_FOUND`, `PROFILE_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

**Rationale:** Combines the three dispatcher gates (profile exists, skills resolve, toolsets available) into a single pre-flight. Not P0 because the dispatcher already validates these at dispatch time.

---

### 1.2 Task CRUD

#### `create_task`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new Kanban task |
| **Inputs** | `{ title, body?, assignee?, priority?, parent_ids?, tenant?, session_id?, triage?, idempotency_key?, workspace_kind?, workspace_path?, skills?, model?, provider?, goal_mode?, goal_max_turns?, max_runtime_seconds? }` |
| **Outputs** | `{ created, idempotent_replay, task_id, board, title, status, assignee, priority, parent_ids, child_ids, created_by, created_at }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:create` |
| **PRIMITIVE** | `kanban_db.create_task()` via `HermesCreateAdapter` |
| **Validation** | title required (1-512 chars); parent_ids verified to exist; assignee verified via `profile_exists()`; idempotency_key prevents duplicate creation; workspace_kind must be one of scratch/dir/worktree |
| **Errors** | `VALIDATION_ERROR` (bad input), `BOARD_NOT_FOUND`, `TASK_NOT_FOUND` (parent), `PROFILE_NOT_FOUND` (assignee), `IDEMPOTENCY_CONFLICT` |
| **Priority** | `P0` |
| **Target** | V4 |

**Evidence basis:** Current MCP `CreateTaskInput` (schemas.py:145-157) is a strict subset of Hermes' canonical args. V4 extends with `skills`, `model`, `provider`, `goal_mode`, `workspace_kind`, `workspace_path`.

**P0 blocker resolution:** The `skills` field in task creation is preserved in order; force-load appends at dispatch time (e.g. `sdlc-review` for review lane). V4 must document this union semantics (P0-5).

---

#### `get_task`

| Field | Value |
|-------|-------|
| **Purpose** | Get full task detail including body, parents, children, runs, attachments |
| **Inputs** | `{ task_id: string }` |
| **Outputs** | `TaskDetail` (schemas.py:255-267) |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.get_task()` + `parent_ids()` + `child_ids()` + `list_runs()` + `list_attachments()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `list_tasks`

| Field | Value |
|-------|-------|
| **Purpose** | List tasks with filtering and pagination |
| **Inputs** | `{ status?, assignee?, tenant?, session_id?, include_archived?, limit?, order_by? }` |
| **Outputs** | `TaskListView` (schemas.py:249-253) |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.list_tasks()` |
| **Validation** | status must be valid TaskStatus enum; limit 1-100 |
| **Errors** | `VALIDATION_ERROR` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `edit_task`

| Field | Value |
|-------|-------|
| **Purpose** | Update mutable task fields |
| **Inputs** | `{ task_id, title?, body?, priority?, assignee?, status?, skills?, model?, provider? }` |
| **Outputs** | `TaskDetail` (updated) |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.edit_task()` |
| **Validation** | Task must exist; status transitions must be valid; assignee verified via `profile_exists()` if changed |
| **Errors** | `TASK_NOT_FOUND`, `VALIDATION_ERROR`, `PROFILE_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Priority** | `P0` |
| **Target** | V4 |

**Note:** Status transitions are constrained by the state machine (triage→todo→scheduled→ready→running→blocked→review→done→archived). V4 should expose transition validation.

---

#### `get_task_graph`

| Field | Value |
|-------|-------|
| **Purpose** | Get parent/child dependency graph for a task |
| **Inputs** | `{ task_id, depth?, max_nodes? }` |
| **Outputs** | `TaskGraphView` (schemas.py:282-287) |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.parent_ids()` + `kanban_db.child_ids()` recursive |
| **Validation** | Task must exist; depth 0-8; max_nodes 1-500 |
| **Errors** | `TASK_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

### 1.3 Task lifecycle (status transitions)

#### `promote_task`

| Field | Value |
|-------|-------|
| **Purpose** | Advance task to next status (ready→running, todo→ready, etc.) |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ task_id, old_status, new_status }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.promote_task()` |
| **Validation** | Task must exist; transition must be valid |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `block_task`

| Field | Value |
|-------|-------|
| **Purpose** | Set task to blocked with reason |
| **Inputs** | `{ task_id, reason, kind? }` |
| **Outputs** | `{ task_id, status: "blocked", block_kind, reason }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.block_task()` |
| **Validation** | Task must exist; reason required |
| **Errors** | `TASK_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `unblock_task`

| Field | Value |
|-------|-------|
| **Purpose** | Remove block from task |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ task_id, status }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.unblock_task()` |
| **Validation** | Task must exist; task must be blocked |
| **Errors** | `TASK_NOT_FOUND`, `TASK_NOT_BLOCKED` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `request_review`

| Field | Value |
|-------|-------|
| **Purpose** | Move task to review column |
| **Inputs** | `{ task_id, summary, metadata?, reviewer? }` |
| **Outputs** | `{ task_id, status: "review" }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.request_review()` |
| **Validation** | Task must exist; task must be running |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `complete_task`

| Field | Value |
|-------|-------|
| **Purpose** | Mark task done with summary and metadata |
| **Inputs** | `{ task_id, summary?, result?, metadata?, artifacts?, created_cards? }` |
| **Outputs** | `{ task_id, status: "done", completed_at }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.complete_task()` |
| **Validation** | Task must exist; created_cards verified to exist |
| **Errors** | `TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION`, `PHANTOM_CARD_REFERENCE` |
| **Priority** | `P0` |
| **Target** | V4 |

---

### 1.4 Comments and Activity

#### `add_comment`

| Field | Value |
|-------|-------|
| **Purpose** | Add a comment to a task |
| **Inputs** | `{ task_id, body }` |
| **Outputs** | `AddCommentResult` (schemas.py:125-132) |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:create` |
| **PRIMITIVE** | `kanban_db.add_comment()` |
| **Validation** | Task must exist; body 1-16000 chars |
| **Errors** | `TASK_NOT_FOUND` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `get_activity`

| Field | Value |
|-------|-------|
| **Purpose** | Get events, comments, runs, and log for a task |
| **Inputs** | `{ task_id, max_items?, log_bytes? }` |
| **Outputs** | `ActivityView` (schemas.py:297-304) |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.list_events()` + `list_comments()` + `list_runs()` + `get_task_log()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Priority** | `P0` |
| **Target** | V4 |

---

### 1.5 Attachments

#### `attach_file`

| Field | Value |
|-------|-------|
| **Purpose** | Upload a file to a task (base64 inline) |
| **Inputs** | `{ task_id, content_base64, filename, content_type? }` |
| **Outputs** | `{ filename, content_type, size, created_at }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:create` |
| **PRIMITIVE** | `kanban_db.store_attachment_bytes()` |
| **Validation** | Task must exist; base64 decode must succeed; size ≤ `KANBAN_ATTACHMENT_MAX_BYTES` (25MB); filename sanitized via `_safe_attachment_name()` |
| **Errors** | `TASK_NOT_FOUND`, `VALIDATION_ERROR` (bad base64), `SIZE_LIMIT_EXCEEDED`, `FILENAME_REJECTED` |
| **Priority** | `P0` |
| **Target** | V4 |

**P0-1 resolution:** Current MCP `attach(local_path=...)` is architecturally wrong for remote clients — it requires server filesystem access that remote clients cannot provide (t_2499ad0a). V4 MUST add `content_base64` field. The `local_path` variant is retained for server-side automation only.

**P0-2 resolution:** Size cap must be unified to 25MB across all surfaces (agent = 25MB, MCP connector default = 10MB). Document divergence until connector is updated.

---

#### `list_attachments`

| Field | Value |
|-------|-------|
| **Purpose** | List attachments for a task |
| **Inputs** | `{ task_id }` |
| **Outputs** | `{ items: [{ filename, content_type, size, uploaded_by, created_at }] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.list_attachments()` |
| **Validation** | Task must exist |
| **Errors** | `TASK_NOT_FOUND` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `get_attachment`

| Field | Value |
|-------|-------|
| **Purpose** | Get attachment content (base64 encoded) |
| **Inputs** | `{ task_id, filename }` |
| **Outputs** | `{ filename, content_type, size, content_base64 }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.get_attachment_bytes()` |
| **Validation** | Task and attachment must exist |
| **Errors** | `TASK_NOT_FOUND`, `ATTACHMENT_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `remove_attachment`

| Field | Value |
|-------|-------|
| **Purpose** | Remove an attachment from a task |
| **Inputs** | `{ task_id, filename }` |
| **Outputs** | `{ removed: boolean }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.remove_attachment()` |
| **Validation** | Task and attachment must exist |
| **Errors** | `TASK_NOT_FOUND`, `ATTACHMENT_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

### 1.6 Workers / Runs / Inspect / Terminate

#### `list_active_workers`

| Field | Value |
|-------|-------|
| **Purpose** | List currently running workers with heartbeat/claim info |
| **Inputs** | `{}` |
| **Outputs** | `{ items: [{ run_id, task_id, profile, worker_pid, started_at, last_heartbeat, claim_expiry, runtime_seconds }] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | Dashboard plugin API `GET /api/plugins/kanban/workers/active` (plugin_api.py:1551-1609) |
| **Validation** | None |
| **Errors** | `BACKEND_UNAVAILABLE` if dashboard plugin not mounted |
| **Priority** | `P0` |
| **Target** | V4 |

**Note:** Requires Kanban dashboard plugin to be enabled/mounted in the running gateway. Live mount status is STILL_NOT_PROVEN (t_ad6925aa).

---

#### `get_run`

| Field | Value |
|-------|-------|
| **Purpose** | Get run details for a specific attempt |
| **Inputs** | `{ run_id: integer }` |
| **Outputs** | `TaskRunRecord` (schemas.py:210-220) |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | Dashboard `GET /api/plugins/kanban/runs/{run_id}` (plugin_api.py:1612-1631) |
| **Validation** | Run must exist |
| **Errors** | `RUN_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `inspect_run`

| Field | Value |
|-------|-------|
| **Purpose** | Get live process inspection for a running worker |
| **Inputs** | `{ run_id: integer }` |
| **Outputs** | `{ alive, pid, cpu_percent, rss_bytes, vms_bytes, threads, fds, status, create_time, cmdline }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | Dashboard `GET /api/plugins/kanban/runs/{run_id}/inspect` (plugin_api.py:1634-1700, psutil) |
| **Validation** | Run must exist; PID must be recorded; psutil must be available |
| **Errors** | `RUN_NOT_FOUND`, `PROCESS_NOT_ALIVE`, `PSUTIL_UNAVAILABLE` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `terminate_run`

| Field | Value |
|-------|-------|
| **Purpose** | Terminate/reclaim a running worker |
| **Inputs** | `{ run_id: integer }` |
| **Outputs** | `{ ok, run_id, task_id }` |
| **Risk** | `WRITE` (DESTRUCTIVE) |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | Dashboard `POST /api/plugins/kanban/runs/{run_id}/terminate` → `reclaim_task()` (plugin_api.py:1702-1751) |
| **Validation** | Run must exist; must not be already ended |
| **Errors** | `RUN_NOT_FOUND`, `RUN_ALREADY_ENDED` |
| **Priority** | `P1` |
| **Target** | V4 |

**Safety note:** This calls `reclaim_task()` which writes task/run state. It is the only destructive operation in the worker/run surface. V4 should require explicit confirmation or admin scope.

---

### 1.7 Gateway / Dispatcher

#### `gateway_status`

| Field | Value |
|-------|-------|
| **Purpose** | Get gateway process status and configuration |
| **Inputs** | `{}` |
| **Outputs** | `{ gateway_running, pid, profiles: [{ name, status, pid }], dispatch_enabled, dispatch_interval, stale_timeout }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes gateway status` + `hermes gateway list` |
| **Validation** | None |
| **Errors** | `GATEWAY_UNAVAILABLE` |
| **Priority** | `P1` |
| **Target** | V4 |

**Note:** Gateway status is profile-scoped. A running default gateway does NOT imply the investigator profile's systemd unit is running (t_ad6925aa).

---

#### `dispatcher_status`

| Field | Value |
|-------|-------|
| **Purpose** | Get dispatcher tick state, lock ownership, and queue |
| **Inputs** | `{ board?: string }` |
| **Outputs** | `{ dispatch_enabled, lock_owner, tick_interval, last_tick, auto_decompose, queue: { ready, blocked, running, review } }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.dispatch_once()` status + board stats |
| **Validation** | Board must exist |
| **Errors** | `BOARD_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

### 1.8 Native Tool Registry

#### `list_native_tools`

| Field | Value |
|-------|-------|
| **Purpose** | List all registered native tools with metadata |
| **Inputs** | `{ toolset?, origin?, risk_class? }` |
| **Outputs** | `{ items: [{ name, toolset, origin, description, risk_class, availability, check_fn, requires_env }], total }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `tools/registry.py` `ToolRegistry.get_all_entries()` |
| **Validation** | Filter values must be valid enums |
| **Errors** | `INTERNAL_ERROR` |
| **Priority** | `P1` |
| **Target** | V4 |

**Evidence:** 87 unique leaf tools, 31 registry toolsets, all BUILTIN origin in current env (t_5caf4595).

---

#### `get_native_tool`

| Field | Value |
|-------|-------|
| **Purpose** | Get full details for a specific native tool |
| **Inputs** | `{ tool_name: string }` |
| **Outputs** | `{ name, toolset, origin, schema, description, emoji, risk_class, availability, check_fn, requires_env, is_async }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `ToolRegistry.get_entry(name)` |
| **Validation** | Tool must exist |
| **Errors** | `TOOL_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `get_profile_tools`

| Field | Value |
|-------|-------|
| **Purpose** | Get OpenAI-format tool definitions for a specific profile's effective toolset |
| **Inputs** | `{ profile: string }` |
| **Outputs** | `{ items: [{ name, toolset, schema }], toolset_names }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `ToolRegistry.get_definitions(tool_names)` filtered by `_resolve_worker_cli_toolsets()` |
| **Validation** | Profile must exist |
| **Errors** | `PROFILE_NOT_FOUND` |
| **Priority** | `P1` |
| **Target** | V4 |

---

### 1.9 Kanban Configuration

#### `get_kanban_config`

| Field | Value |
|-------|-------|
| **Purpose** | Get effective Kanban configuration for current board |
| **Inputs** | `{}` |
| **Outputs** | `{ dispatch_in_gateway, dispatch_interval_seconds, failure_limit, auto_decompose, auto_decompose_per_tick, dispatch_stale_timeout_seconds, max_in_progress, max_in_progress_per_profile, orchestrator_profile, default_assignee, ... }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `config_defaults.py` defaults + active profile config merge |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Priority** | `P2` |
| **Target** | V4.x |

**Note:** Global pause (ESTOP) exists; board-local pause is ABSENT (t_ef94f514). V4 documentation must clarify this.

---

#### `update_kanban_config`

| Field | Value |
|-------|-------|
| **Purpose** | Update Kanban orchestration settings |
| **Inputs** | `{ orchestrator_profile?, default_assignee?, auto_decompose?, auto_decompose_per_tick?, auto_promote_children? }` |
| **Outputs** | `{ updated: boolean, fields: string[] }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | Dashboard `PUT /orchestration` (plugin_api.py) |
| **Validation** | Values must be valid; orchestrator_profile must exist |
| **Errors** | `VALIDATION_ERROR`, `PROFILE_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

### 1.10 Board Management

#### `list_boards`

| Field | Value |
|-------|-------|
| **Purpose** | List all available boards |
| **Inputs** | `{ include_archived? }` |
| **Outputs** | `BoardListView` (schemas.py:64-67) |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.list_boards()` |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `create_board`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new Kanban board |
| **Inputs** | `{ slug, name?, description?, icon?, color? }` |
| **Outputs** | `CreateBoardResult` (schemas.py:110-117) |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:board:create` |
| **PRIMITIVE** | `HermesBoardAdminAdapter.create_board()` |
| **Validation** | Slug must match pattern; board must not exist; quota check if configured |
| **Errors** | `VALIDATION_ERROR`, `BOARD_EXISTS`, `QUOTA_EXCEEDED`, `ARCHIVED_SLUG_RESERVED` |
| **Priority** | `P1` |
| **Target** | V4 |

---

### 1.11 Notifications

#### `subscribe_notifications`

| Field | Value |
|-------|-------|
| **Purpose** | Subscribe to task/board notifications |
| **Inputs** | `{ task_id?, board?, event_kinds? }` |
| **Outputs** | `{ subscription_id, cursor }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:create` |
| **PRIMITIVE** | `kanban_db.subscribe_notification()` |
| **Validation** | Task or board must exist |
| **Errors** | `TASK_NOT_FOUND`, `BOARD_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

#### `poll_notifications`

| Field | Value |
|-------|-------|
| **Purpose** | Poll for new notifications since last cursor |
| **Inputs** | `{ subscription_id, cursor? }` |
| **Outputs** | `{ items: [{ event_kind, task_id, payload, created_at }], next_cursor, truncated }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.poll_notifications()` |
| **Validation** | Subscription must exist |
| **Errors** | `SUBSCRIPTION_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

### 1.12 Scopes / Auth

#### `get_session_info`

| Field | Value |
|-------|-------|
| **Purpose** | Get current session and scope information |
| **Inputs** | `{}` |
| **Outputs** | `{ session_id, board, profile, scopes: string[], created_at }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | Session context from MCP connection |
| **Validation** | None |
| **Errors** | None |
| **Priority** | `P1` |
| **Target** | V4 |

**Rationale:** ChatGPT MCP sessions carry implicit board scope. V4 should make this explicit so the client knows what it can access.

---

### 1.13 Runtime / Build / Provenance

#### `get_build_info`

| Field | Value |
|-------|-------|
| **Purpose** | Get Hermes build version and provenance |
| **Inputs** | `{}` |
| **Outputs** | `{ hermes_version, upstream_sha, local_head, install_dir, python_version, openai_sdk_version }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes version` output parsing |
| **Validation** | None |
| **Errors** | None |
| **Priority** | `P2` |
| **Target** | V4.x |

---

## 2. Error model

All tools return errors in a consistent format:

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task t_abc123 does not exist on board hermes-chatgpt-mcp",
    "details": {}
  }
}
```

**Standard error codes:**

| Code | HTTP Equivalent | Description |
|------|-----------------|-------------|
| `TASK_NOT_FOUND` | 404 | Task does not exist |
| `PROFILE_NOT_FOUND` | 404 | Profile does not exist |
| `BOARD_NOT_FOUND` | 404 | Board does not exist |
| `SKILL_NOT_FOUND` | 404 | Skill does not exist |
| `TOOL_NOT_FOUND` | 404 | Native tool does not exist |
| `RUN_NOT_FOUND` | 404 | Run does not exist |
| `ATTACHMENT_NOT_FOUND` | 404 | Attachment does not exist |
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `INVALID_STATUS_TRANSITION` | 409 | State machine violation |
| `SIZE_LIMIT_EXCEEDED` | 413 | Attachment exceeds 25MB cap |
| `FILENAME_REJECTED` | 400 | Filename failed sanitization |
| `IDEMPOTENCY_CONFLICT` | 409 | Idempotency key collision |
| `BOARD_EXISTS` | 409 | Board slug already taken |
| `QUOTA_EXCEEDED` | 429 | Board count limit reached |
| `TASK_NOT_BLOCKED` | 409 | Task is not in blocked state |
| `PHANTOM_CARD_REFERENCE` | 400 | created_cards references non-existent task |
| `BACKEND_UNAVAILABLE` | 503 | Dashboard plugin or gateway not reachable |
| `PROCESS_NOT_ALIVE` | 404 | Worker PID no longer running |
| `PSUTIL_UNAVAILABLE` | 501 | Process inspection not available |
| `INTERNAL_ERROR` | 500 | Unexpected internal failure |

---

## 3. Pagination / boundedness / idempotency

### Pagination
- `list_tasks`: `limit` field (1-100, default 50); `truncated` flag in response
- `list_native_tools`: server-side cap at 200 items; `total` field indicates unfiltered count
- `get_activity`: `max_items` field (1-200, default 100); `truncated` flag
- `poll_notifications`: cursor-based pagination; `truncated` flag

### Boundedness
- All list operations have hard caps to prevent unbounded responses
- `get_task_graph`: `max_nodes` (1-500) and `depth` (0-8) caps
- `get_activity`: `log_bytes` cap (0-32000)

### Idempotency
- `create_task`: `idempotency_key` field prevents duplicate creation; returns `idempotent_replay: true` on match
- `add_comment`: no idempotency key (comments are append-only)
- Other mutations: not idempotent by default; callers should use task_id + timestamp for dedup

---

## 4. Evidence/provenance fields

Every response includes:

```json
{
  "board": "hermes-chatgpt-mcp",
  "hermes_version": "0.20.2",
  "source_head": "39cfd1ab41",
  "generated_at": 1787160000
}
```

Task-level provenance:
- `created_by`: always `"chatgpt_mcp"` for MCP-created tasks
- `claim.provenance`: records who claimed the task
- `task_runs[].profile`: which profile ran the attempt
- `task_runs[].metadata`: arbitrary machine-readable evidence

---

## 5. Tools explicitly NOT exposed (DO_NOT_EXPOSE)

| Tool | Rationale |
|------|-----------|
| `dispatch_task` | Dispatcher is server-side; remote dispatch would bypass singleton lock, concurrency caps, and board-pinned spawn |
| `spawn_worker` | Same as dispatch — spawn is an internal server operation |
| `pause_dispatch` / `resume_dispatch` | Global ESTOP exists via `hermes pause/resume`; board-local pause is ABSENT. Exposing global pause via MCP is dangerous without auth confirmation |
| `reclaim_task` | Destructive; only via `terminate_run` with admin scope |
| `edit_config` | System config mutation is dangerous; only `update_kanban_config` for orchestration settings |
| `delete_task` | No delete operation exists in Hermes; tasks can only be archived |
| `get_secret` / `set_secret` | Credentials must never cross MCP boundary |
| `get_heartbeat` | Write operation (writes heartbeat event); workers call this internally |
| `force_dispatch` | Bypasses all safety checks |

---

## 6. STILL_NOT_PROVEN items preserved

| Item | Classification | Impact on V4 spec |
|------|---------------|-------------------|
| Temporary skills per task (exact semantics) | STILL_NOT_PROVEN | V4 `create_task` includes `skills` field; resolution semantics documented as "forwarded verbatim to worker, union with force-load" |
| Fine-grained profile permissions | STILL_NOT_PROVEN | Treated as advisory metadata only; not enforced by Hermes core |
| Historical exact reason for C-IMPL-5 crash | STILL_NOT_PROVEN | Historical; does not affect current contract |
| Deployed connector SHA | STILL_NOT_PROVEN | Implementation concern; V4 spec binds to v0.20.2 local evidence |
| Live dashboard plugin API auth | STILL_NOT_PROVEN | Integration test needed before V4 release |
| Live `/kanban` connector delivery/ACL | UNSAFE_TO_TEST | V4 spec notes this as integration concern |
| Kanban terminate live behavior | UNSAFE_TO_TEST | V4 spec includes `terminate_run` with admin scope; live behavior untested |
| Heartbeat reclaim live behavior | UNSAFE_TO_TEST | Dispatcher behavior documented from source; live not tested |

---

## 7. P0 blockers from synthesis

| ID | Description | V4 spec resolution |
|----|-------------|-------------------|
| P0-1 | Add `content_base64` to MCP connector AttachInput | `attach_file` tool defined with `content_base64` field |
| P0-2 | Unify attachment size cap (25MB vs 10MB) | V4 spec documents 25MB as canonical; connector update required |
| P0-3 | Pin deployed connector SHA | Not a spec concern; implementation/ops gate |
| P0-4 | V4 skill queries: never use `hermes skills inspect` | `list_skills` uses `skills list`; `get_skill` uses `skill_view` |
| P0-5 | Preserve sdlc-review force-load pattern | Documented in `create_task` notes; force-load is dispatcher-internal |

---

## 8. Current OAuth Scope Vocabulary (CURRENT)

The following scopes are **proven to exist** in the current Hermes ChatGPT MCP connection flow:

| Scope | Description | Used by |
|-------|-------------|---------|
| `hermes:read` | Read-only access to tasks, profiles, skills, workers, attachments, gateway, native tools | All READ operations |
| `hermes:create` | Create new tasks, comments, attachments, subscriptions | `create_task`, `add_comment`, `attach_file`, `subscribe_notifications` |
| `hermes:manage` | Mutate existing tasks, configurations, terminate workers | `edit_task`, `complete_task`, `promote_task`, `block_task`, `unblock_task`, `request_review`, `remove_attachment`, `terminate_run`, `update_kanban_config` |
| `hermes:board:create` | Create new boards | `create_board` |
| `offline_access` | Connection flow only — refresh token | Not a tool scope; handled in OAuth handshake |

---

## 9. PROPOSED V4 Fine-Grained Scope Taxonomy (PROPOSED)

The following finer-grained scopes are **PROPOSED** for future V4.x releases to enable least-privilege delegation. They do NOT exist in the current connector and MUST be labeled PROPOSED in any implementation.

| Proposed Scope | Maps from Current | Intended Use |
|----------------|-------------------|--------------|
| `hermes:task:read` | `hermes:read` | Read tasks, task graphs, activity |
| `hermes:task:create` | `hermes:create` | Create tasks |
| `hermes:task:write` | `hermes:manage` | Edit, complete, promote, block, unblock, request_review tasks |
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

| Current Scope | → | Proposed Scopes |
|---------------|---|-----------------|
| `hermes:read` | → | `hermes:task:read`, `hermes:attachment:read`, `hermes:profile:read`, `hermes:worker:read`, `hermes:gateway:read`, `hermes:tool:read`, `hermes:config:read`, `hermes:board:read`, `hermes:notification:read` |
| `hermes:create` | → | `hermes:task:create`, `hermes:comment:create`, `hermes:attachment:create`, `hermes:notification:create` |
| `hermes:manage` | → | `hermes:task:write`, `hermes:attachment:delete`, `hermes:worker:terminate`, `hermes:config:write` |
| `hermes:board:create` | → | `hermes:board:create` (unchanged) |

**Note:** V4 tools use CURRENT scope names. Any implementation adopting PROPOSED scopes MUST provide backward compatibility via scope aggregation (e.g., grant `hermes:read` implies all `hermes:*:read` subscopes).

---

## Appendix A: Status state machine

```
triage → todo → scheduled → ready → running → blocked
                                      ↓         ↓
                                    review ←───┘
                                      ↓
                                    done → archived
```

Valid transitions:
- `triage` → `todo`
- `todo` → `scheduled`, `ready`
- `scheduled` → `ready`
- `ready` → `running` (dispatcher or manual)
- `running` → `blocked`, `review`, `done`
- `blocked` → `ready`, `running`
- `review` → `done`, `running` (request-changes)
- `done` → `archived`

---

## Appendix B: Workspace kinds

| Kind | Description | Branch enforcement |
|------|-------------|-------------------|
| `scratch` | Temporary workspace under board workspaces root | NOT_APPLICABLE |
| `dir` | Persistent directory; requires absolute path | Path must be absolute |
| `worktree` | Git worktree linked to repo; auto-generated branch | Branch name required or auto-generated `wt/<task-id>` |

---

*End of V4 Control Plane Spec Draft*