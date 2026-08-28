# V4 Control Plane Spec

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)
**Derived from:** t_484d4ab0 (`V4-CONTROL-PLANE-SPEC-DRAFT.md`)

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
| **Outputs** | `{ items: [{ name, description, model_provider, skill_count, effective_toolsets, disponible, spawnable }] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes_cli.profiles.list_profiles()` + `hermes_cli.tools_config._get_platform_tools()` |
| **Validation** | None (pure read) |
| **Errors** | `BOARD_NOT_FOUND` if board invalid; `INTERNAL_ERROR` if profile registry unavailable |
| **Priority** | `P0` |
| **Target** | V4 |

**Rationale:** Profile discovery is the entry point for all worker routing. Without it, a ChatGPT client cannot determine which profiles exist, what models they use, or what skills they have. Evidence: 14 profiles confirmed via `hermes profile list` (t_c2257b50). Descriptions, model/provider, and skill counts are all RESOLVED_LOCALLY.

**Notes:**
- `spawnable` field distinguishes `dispatcher_eligible` (predicate-level) from `end_to_end_observed` (only investigator/profile-architect/operator/software-architect observed)
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
| **Priority** | `P0` |
| **Target** | V4 |

**Caveat:** P0-5: Force-load pattern (sdlc-review) must be documented as union semantics — creation skills preserved, force-load appends at dispatch time.

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
| **Priority** | `P0` |
| **Target** | V4 |

**Rationale:** Combines the three dispatcher gates (profile exists, skills resolve, toolsets available) into a single pre-flight. Not P0 in isolation — the dispatcher already validates these at dispatch time. Included in P0 for completeness of the profile/skills discovery surface.

---

### 1.2 Task CRUD

#### `create_task`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new Kanban task |
| **Inputs** | `{ title, body?, assignee?, priority?, parent_ids?, tenant?, idempotency_key?, workspace_kind?, workspace_path?, skills?, model?, provider?, goal_mode?, goal_max_turns?, max_runtime_seconds?, initial_status?, project?, triage? }` |
| **Outputs** | `{ created, idempotent_replay, task_id, board, title, status, assignee, priority, parent_ids, child_ids, created_by, created_at }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:create` |
| **PRIMITIVE** | `kanban_db.create_task()` via `HermesCreateAdapter` |
| **Validation** | title required (1-512 chars); parent_ids verified to exist; assignee verified via `profile_exists()`; idempotency_key prevents duplicate creation; workspace_kind must be scratch/dir/worktree |
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
| **Risk** | `ADMIN` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | Dashboard `POST /api/plugins/kanban/runs/{run_id}/terminate` (calls `reclaim_task()`) |
| **Validation** | Run must exist; run must be active |
| **Errors** | `RUN_NOT_FOUND`, `RUN_NOT_ACTIVE` |
| **Priority** | `P0` |
| **Target** | V4 |

**Caveat:** Routes through `reclaim_task`. UNSAFE_TO_TEST for live behavior.

---

### 1.7 Boards

#### `list_boards`

| Field | Value |
|-------|-------|
| **Purpose** | List all Kanban boards |
| **Inputs** | `{}` |
| **Outputs** | `{ items: [{ slug, name, created_at, default_workdir }] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.list_boards()` |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Priority** | `P1` |
| **Target** | V4 |

---

#### `create_board`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new Kanban board |
| **Inputs** | `{ slug, name?, default_workdir? }` |
| **Outputs** | `{ slug, name, created_at, default_workdir }` |
| **Risk** | `ADMIN` |
| **Required scope** | `hermes:board:create` |
| **PRIMITIVE** | `kanban_db.init_db()` |
| **Validation** | slug must be unique; valid slug format |
| **Errors** | `BOARD_ALREADY_EXISTS`, `VALIDATION_ERROR` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `get_board`

| Field | Value |
|-------|-------|
| **Purpose** | Get board metadata and capabilities |
| **Inputs** | `{ board?: string }` (defaults to session board) |
| **Outputs** | `{ slug, name, created_at, default_workdir, capabilities: { read, write, admin, create, manage } }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.get_board()` + capability resolution |
| **Validation** | Board must exist |
| **Errors** | `BOARD_NOT_FOUND` |
| **Priority** | `P0` |
| **Target** | V4 |

**Known issue:** `get_board` capability readback inconsistent with successful writes.

---

### 1.8 Runtime / Build / Provenance

#### `get_build_info`

| Field | Value |
|-------|-------|
| **Purpose** | Get build version, SHA, install info |
| **Inputs** | `{}` |
| **Outputs** | `{ hermes_version, upstream_sha, local_head, install_dir, install_method, python_version, openai_sdk_version, executable }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes version` output parsing |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `gateway_status`

| Field | Value |
|-------|-------|
| **Purpose** | Get gateway lifecycle status |
| **Inputs** | `{}` |
| **Outputs** | `{ gateway_running, pid, profile, dispatch_enabled, connector_label, api_server_port, uptime }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `hermes gateway status` + runtime introspection |
| **Validation** | None |
| **Errors** | `BACKEND_UNAVAILABLE` |
| **Priority** | `P0` |
| **Target** | V4 |

---

#### `get_session_info`

| Field | Value |
|-------|-------|
| **Purpose** | Get current MCP session metadata |
| **Inputs** | `{}` |
| **Outputs** | `{ board, profile, scopes, connected_at, client_info? }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | SessionManager introspection |
| **Validation** | None |
| **Errors** | `INTERNAL_ERROR` |
| **Priority** | `P1` |
| **Target** | V4 |

---

### 1.9 Notifications

#### `subscribe_notifications`

| Field | Value |
|-------|-------|
| **Purpose** | Subscribe to task/board event notifications |
| **Inputs** | `{ channel, filter?, board? }` |
| **Outputs** | `{ subscription_id }` |
| **Risk** | `WRITE` |
| **Required scope** | `hermes:create` |
| **PRIMITIVE** | `kanban_db.subscribe()` |
| **Validation** | channel must be valid; board defaults to session board |
| **Errors** | `VALIDATION_ERROR`, `BOARD_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

#### `poll_notifications`

| Field | Value |
|-------|-------|
| **Purpose** | Poll for pending notifications |
| **Inputs** | `{ subscription_id, max_items? }` |
| **Outputs** | `{ items: [{ event_type, task_id, payload, timestamp }] }` |
| **Risk** | `READ` |
| **Required scope** | `hermes:read` |
| **PRIMITIVE** | `kanban_db.poll_notifications()` |
| **Validation** | subscription_id must exist |
| **Errors** | `SUBSCRIPTION_NOT_FOUND` |
| **Priority** | `P2` |
| **Target** | V4.x |

---

### 1.10 Admin / Config

#### `update_kanban_config`

| Field | Value |
|-------|-------|
| **Purpose** | Update Kanban configuration |
| **Inputs** | `{ key, value }` |
| **Outputs** | `{ key, value, updated_at }` |
| **Risk** | `ADMIN` |
| **Required scope** | `hermes:manage` |
| **PRIMITIVE** | `kanban_db.update_config()` |
| **Validation** | key must be valid config key |
| **Errors** | `CONFIG_KEY_INVALID`, `INTERNAL_ERROR` |
| **Priority** | `P1` |
| **Target** | V4 |

---

## 2. Scope Model (V4 Target Contract)

The adapter scope model below is the **V4 target contract**, not a claim that every current live tool has a proven scope mapping. The final catalog is authoritative for current exposure/status/scope distinctions.

| Scope | V4 target access | V4 target tools |
|-------|------------------|-----------------|
| `hermes:read` | Implicit in MCP connection | All read-only tools |
| `hermes:create` | Granted at connection init | Create tasks, comments, attachments, subscriptions |
| `hermes:manage` | Granted at connection init | Mutate tasks, configs, terminate workers, update kanban config |
| `hermes:board:create` | Granted at connection init | Create boards |

**Current proven mappings:** `hermes:read` is the read-only baseline; `hermes:create` is proven for `create_task`; `hermes:manage` is proven for `add_comment` and `assign_task`; `hermes:board:create` is proven for `create_board`; `offline_access` is connection-only. All other current tool scopes are `NOT_PROVEN / inherited policy`.

**Note:** Fine-grained profile permissions (`kanban.capabilities/refuses`) are NOT enforced by Hermes core (t_c2257b50). V4 treats them as advisory routing metadata only.

---

## 3. Board Scope

The board scope is established at MCP connection initialization and cannot be changed during the session. This prevents a remote client from:
- Reading tasks from boards it was not connected to
- Creating tasks on unauthorized boards
- Terminating workers on other boards

Board scope is validated on every operation.

---

## 4. P0 Blocker Summary

| Blocker | Description | Resolution |
|---------|-------------|------------|
| P0-1 | MCP AttachInput missing `content_base64` | Add to schema; agent already supports it |
| P0-2 | Size cap mismatch (25MB agent vs 10MB MCP) | Unify to 25MB policy |
| P0-3 | Deployed connector SHA unknown | Pin via existing primitives before release |
| P0-4 | `hermes skills inspect` hub-only | Document `skills list`/`skill_view` as required |
| P0-5 | sdlc-review force-load at dispatch | Preserve pattern; document union semantics |

---

## 5. References

- [MCP_TOPOLOGY_ADR.md](MCP_TOPOLOGY_ADR.md) (companion document)
- [CURRENT_STATE.md](CURRENT_STATE.md) (evidence baseline)
- `hermes-chatgpt-mcp/hermes_chatgpt_mcp/schemas.py` (current MCP schemas)
- `hermes-chatgpt-mcp/hermes_chatgpt_mcp/command.py` (current adapter pattern)
- `hermes-agent/hermes_cli/kanban_db.py` (Hermes Kanban core)
- `hermes-agent/plugins/kanban/dashboard/plugin_api.py` (dashboard API)
- `hermes-agent/tools/registry.py` (native tool registry)