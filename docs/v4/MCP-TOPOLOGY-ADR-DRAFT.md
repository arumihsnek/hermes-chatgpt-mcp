# MCP Topology ADR — Draft

**Date:** 2026-08-19
**Author:** software-architect (t_f96c8f07)
**Status:** DRAFT — no implementation, no repo edits
**Decision:** Single MCP connector with privilege-separated internal adapters
**Supersedes:** t_f96c8f07
**Artifact lifecycle issue:** post_complete_workspace_changes_not_durable

---

## 1. Context

The Hermes ChatGPT MCP control plane needs to expose Kanban task management,
profile/skills introspection, worker/run inspection, attachment handling,
native tool registry access, and gateway/dispatcher status to a remote ChatGPT
client via MCP JSON-RPC.

The design question is whether to expose all functionality through a single
MCP server (the existing `hermes-chatgpt-mcp` connector) or split into
companion MCP servers with separate privilege boundaries.

### Evidence baseline
- Hermes v0.20.2, source HEAD 39cfd1ab41
- Current MCP connector: `hermes-chatgpt-mcp` with schemas.py + command.py
- Board: `hermes-chatgpt-mcp`
- 87 native tools, 14 profiles, 53 enabled skills
- Dashboard plugin API: 4 endpoints (workers/active, runs, inspect, terminate)
- Native API-server: separate `/v1/runs` surface (NOT Kanban)

---

## 2. Decision

**Adopt a single MCP server with internally privilege-separated adapters.**

The V4 control plane will be implemented as a single MCP server process that
exposes all Kanban control-plane tools. Internally, it uses narrow adapter
classes (following the existing `HermesCreateAdapter` and
`HermesCardManagementAdapter` pattern) to boundary-separate read, write, and
admin operations.

---

## 3. Options evaluated

### Option A: Single MCP server (RECOMMENDED)

```
ChatGPT Client
    ↓ MCP JSON-RPC
    ↓
hermes-chatgpt-mcp (single server)
    ├── ReadOnlyAdapter (hermes:read scope)
    │   ├── list_profiles, get_profile, list_skills, get_skill
    │   ├── list_tasks, get_task, get_task_graph, get_activity
    │   ├── list_attachments, get_attachment
    │   ├── list_native_tools, get_native_tool, get_profile_tools
    │   ├── list_boards, gateway_status, get_build_info
    │   └── list_active_workers, get_run, inspect_run
    ├── WriteAdapter (hermes:create, hermes:manage scopes)
    │   ├── create_task, edit_task, complete_task
    │   ├── add_comment, attach_file, remove_attachment
    │   ├── block_task, unblock_task, request_review, promote_task
    │   └── subscribe_notifications, poll_notifications
    └── AdminAdapter (hermes:board:create, hermes:manage scopes)
        ├── create_board, update_kanban_config, terminate_run
        └── [future: pause_dispatch, force_reclaim]
```

**Advantages:**
1. Single deployment artifact — one server to deploy, monitor, upgrade
2. Shared session state — board scope established once per connection
3. Consistent error model — all tools share the same error schema
4. Latency — no inter-MCP-server calls for cross-cutting operations
5. Existing codebase — extends the current `hermes-chatgpt-mcp` package
6. Internal privilege separation — adapter pattern provides clean boundaries
   without the operational cost of separate processes

**Disadvantages:**
1. All scopes share the same server process — a privilege escalation in one
   adapter could theoretically reach another
2. Larger attack surface per deployment unit

### Option B: Companion MCP servers by privilege level

```
ChatGPT Client
    ├── hermes-chatgpt-mcp-read (hermes:read)
    ├── hermes-chatgpt-mcp-write (hermes:create, hermes:manage)
    └── hermes-chatgpt-mcp-admin (hermes:board:create, hermes:manage)
```

**Advantages:**
1. Stronger process-level isolation between read/write/admin
2. Can deploy admin server with additional auth requirements
3. Smaller individual attack surfaces

**Disadvantages:**
1. Three separate deployment artifacts to maintain
2. Cross-server calls for operations that span privilege levels (e.g.,
   `get_task` returns runs which need worker inspection)
3. Session state must be shared or re-established per server
4. ChatGPT MCP client may not support multiple servers with shared context
5. Significant operational overhead for minimal security gain (the adapter
   pattern already provides logical separation)

### Option C: Companion MCP servers by domain

```
ChatGPT Client
    ├── hermes-chatgpt-mcp-kanban (tasks, boards, lifecycle)
    ├── hermes-chatgpt-mcp-profiles (profiles, skills, tools)
    └── hermes-chatgpt-mcp-runtime (workers, runs, gateway)
```

**Advantages:**
1. Domain-focused APIs
2. Independent versioning per domain

**Disadvantages:**
1. Cross-domain operations are common (task creation needs profile validation,
   task completion needs run inspection)
2. Three deployment artifacts with shared database access
3. ChatGPT MCP client may not handle multi-server tool routing
4. No clear privilege boundary benefit — all three need the same DB access

---

## 4. Rationale for Option A

### 4.1 Privilege boundaries are logical, not physical

The Hermes Kanban system already has privilege separation at the adapter level:
- `HermesCreateAdapter` only exposes `create_task`
- `HermesCardManagementAdapter` only exposes `add_comment` and `assign_task`
- `HermesBoardAdminAdapter` only exposes `create_board`

V4 extends this pattern with `ReadOnlyAdapter`, `WriteAdapter`, and
`AdminAdapter`. Each adapter imports only the specific Hermes functions it
needs. This is the same boundary model used by the existing connector.

### 4.2 Latency and session consistency

Kanban operations frequently span domains:
- `create_task` needs profile validation (profiles domain) + DB write (kanban domain)
- `complete_task` needs run inspection (runtime domain) + status transition (kanban domain)
- `get_task_graph` needs parent/child resolution across the same DB

Splitting into separate MCP servers would require either:
- Cross-server RPC (adds latency, complexity, failure modes)
- Duplicated DB connections (resource waste, consistency risk)
- Denormalized state (cache coherence problems)

### 4.3 ChatGPT MCP client compatibility

The ChatGPT MCP client discovers tools from a single server endpoint.
Multiple servers require the client to:
- Know about all server endpoints
- Route tools to the correct server
- Handle partial failures when one server is down

Single-server deployment is the simplest path to reliable ChatGPT integration.

### 4.4 Operational simplicity

One server means:
- One health check
- One log stream
- One upgrade path
- One configuration surface
- One monitoring dashboard

For a control plane that manages 14 profiles, 87 tools, and 53 skills,
operational simplicity is a material benefit.

---

## 5. Architecture

### 5.1 Adapter hierarchy

```
MCP Server (single process)
    │
    ├── SessionManager
    │   ├── Board scope (from MCP connection init)
    │   ├── Profile scope (from session metadata)
    │   └── Auth scopes (hermes:read, hermes:create, hermes:manage, hermes:board:create)
    │
    ├── ReadOnlyAdapter
    │   ├── ProfileIntrospection
    │   │   ├── list_profiles()
    │   │   ├── get_profile()
    │   │   ├── list_skills()
    │   │   └── get_skill()
    │   ├── TaskQueries
    │   │   ├── list_tasks()
    │   │   ├── get_task()
    │   │   ├── get_task_graph()
    │   │   └── get_activity()
    │   ├── AttachmentQueries
    │   │   ├── list_attachments()
    │   │   └── get_attachment()
    │   ├── ToolRegistry
    │   │   ├── list_native_tools()
    │   │   ├── get_native_tool()
    │   │   └── get_profile_tools()
    │   ├── BoardQueries
    │   │   └── list_boards()
    │   ├── RuntimeQueries
    │   │   ├── list_active_workers()
    │   │   ├── get_run()
    │   │   └── inspect_run()
    │   └── SystemQueries
    │       ├── gateway_status()
    │       ├── get_build_info()
    │       └── get_session_info()
    │
    ├── WriteAdapter
    │   ├── TaskMutations
    │   │   ├── create_task()
    │   │   ├── edit_task()
    │   │   ├── complete_task()
    │   │   ├── block_task()
    │   │   ├── unblock_task()
    │   │   ├── request_review()
    │   │   └── promote_task()
    │   ├── CommentMutations
    │   │   └── add_comment()
    │   ├── AttachmentMutations
    │   │   ├── attach_file()
    │   │   └── remove_attachment()
    │   └── NotificationMutations
    │       ├── subscribe_notifications()
    │       └── poll_notifications()
    │
    └── AdminAdapter
        ├── BoardMutations
        │   └── create_board()
        ├── ConfigMutations
        │   └── update_kanban_config()
        └── RuntimeMutations
            └── terminate_run()
```

### 5.2 Scope enforcement

Scope enforcement is adapter-level, not transport-level:

```python
class SessionManager:
    def __init__(self, board: str, scopes: list[str]):
        self.board = board
        self.scopes = scopes

    def require_scope(self, scope: str):
        if scope not in self.scopes:
            raise PermissionError(f"scope {scope!r} not granted")

class ReadOnlyAdapter:
    def __init__(self, session: SessionManager, hermes: Any):
        self.session = session
        self.hermes = hermes
        # No scope check needed — hermes:read is implicit in connection

class WriteAdapter:
    def __init__(self, session: SessionManager, hermes: Any):
        self.session = session
        self.hermes = hermes

    def create_task(self, **kwargs):
        self.session.require_scope("hermes:create")
        # ... delegate to hermes

    def edit_task(self, **kwargs):
        self.session.require_scope("hermes:manage")
        # ... delegate to hermes

class AdminAdapter:
    def __init__(self, session: SessionManager, hermes: Any):
        self.session = session
        self.hermes = hermes

    def terminate_run(self, run_id: int):
        self.session.require_scope("hermes:manage")
        # ... delegate to dashboard plugin API

    def create_board(self, **kwargs):
        self.session.require_scope("hermes:board:create")
        # ... delegate to hermes
```

### 5.3 Scope model

| Scope | Access | Tools |
|-------|--------|-------|
| `hermes:read` | Implicit in MCP connection | All read-only tools |
| `hermes:create` | Granted at connection init | Create tasks, comments, attachments, subscriptions |
| `hermes:manage` | Granted at connection init | Mutate tasks, configs, terminate workers, update kanban config |
| `hermes:board:create` | Granted at connection init | Create boards |

**Note:** Fine-grained profile permissions (`kanban.capabilities/refuses`) are
NOT enforced by Hermes core (t_c2257b50). V4 treats them as advisory routing
metadata only.

### 5.4 Board scope

The board scope is established at MCP connection initialization and cannot be
changed during the session. This prevents a remote client from:
- Reading tasks from boards it was not connected to
- Creating tasks on unauthorized boards
- Terminating workers on other boards

Board scope is validated on every operation:

```python
def _validate_board(self, board: BoardSlug | None) -> str:
    if board is not None and board != self.session.board:
        raise PermissionError("cross-board access denied")
    return self.session.board
```

---

## 6. Migration path

### Phase 1: V4 spec + schema (this document)
- Define all tool schemas in `schemas.py`
- Add `content_base64` to `AttachInput`
- Unify error model
- Document scope requirements

### Phase 2: Adapter implementation
- Implement `ReadOnlyAdapter` with all read tools
- Implement `WriteAdapter` with all write tools
- Implement `AdminAdapter` with admin tools
- Add `SessionManager` for scope enforcement

### Phase 3: Dashboard plugin integration
- Wire `list_active_workers`, `get_run`, `inspect_run`, `terminate_run`
  to dashboard plugin API
- Add health check for dashboard plugin availability
- Graceful degradation if plugin not mounted

### Phase 4: Testing + validation
- Integration tests for all tool contracts
- Privilege escalation tests (write tool without write scope)
- Cross-board access tests
- Attachment upload/download roundtrip tests
- Idempotency key replay tests

---

## 7. Consequences

### Positive
1. Single deployment artifact simplifies operations
2. Adapter pattern provides clean privilege boundaries
3. Consistent error model across all tools
4. Board scope prevents cross-board access
5. Existing codebase extended, not replaced

### Negative
1. Process-level isolation is not achieved — a bug in one adapter could
   theoretically affect others (mitigated by adapter import restrictions)
2. All scopes share the same server process resources
3. Admin tools are in the same process as read tools

### Risks
1. Dashboard plugin availability is STILL_NOT_PROVEN — integration test
   required before V4 release
2. Live connector SHA is STILL_NOT_PROVEN — pin before release
3. `content_base64` upload is new — validate ChatGPT MCP client can send
   base64 in tool arguments

---

## 8. Rejected alternatives

### Rejected: Separate companion MCP for profiles/skills
**Reason:** Profile/skills queries are tightly coupled with task creation
(assignee validation) and dispatch (skill resolution). Splitting would require
cross-server calls for every task creation.

### Rejected: Separate companion MCP for runtime/workers
**Reason:** Worker/run inspection is needed alongside task detail (`get_task`
returns runs). Splitting would fragment the task lifecycle view.

### Rejected: Serverless/Lambda MCP
**Reason:** Hermes Kanban is a long-running control plane with persistent
SQLite state, singleton dispatcher locks, and process-liveness monitoring.
Serverless would break these invariants.

---

## 9. NOT_PROVEN items

| Item | Classification | Impact |
|------|---------------|--------|
| Dashboard plugin API live mount/auth | STILL_NOT_PROVEN | Integration test required before V4 release |
| ChatGPT MCP client base64 support | STILL_NOT_PROVEN | Validate that `content_base64` field is populated by client |
| Live connector SHA | STILL_NOT_PROVEN | Pin deployed version before release |
| Fine-grained profile permissions enforcement | STILL_NOT_PROVEN | Treated as advisory; not enforced |

---

## 10. Current OAuth Scope Vocabulary (CURRENT)

The following scopes are **proven to exist** in the current Hermes ChatGPT MCP connection flow:

| Scope | Description | Used by |
|-------|-------------|---------|
| `hermes:read` | Read-only access to tasks, profiles, skills, workers, attachments, gateway, native tools | All READ operations |
| `hermes:create` | Create new tasks, comments, attachments, subscriptions | `create_task`, `add_comment`, `attach_file`, `subscribe_notifications` |
| `hermes:manage` | Mutate existing tasks, configurations, terminate workers | `edit_task`, `complete_task`, `promote_task`, `block_task`, `unblock_task`, `request_review`, `remove_attachment`, `terminate_run`, `update_kanban_config` |
| `hermes:board:create` | Create new boards | `create_board` |
| `offline_access` | Connection flow only — refresh token | Not a tool scope; handled in OAuth handshake |

---

## 11. PROPOSED V4 Fine-Grained Scope Taxonomy (PROPOSED)

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

## 12. References

- V4-CONTROL-PLANE-SPEC-DRAFT.md (companion document)
- V4-LOCAL-SYNTHESIS-REPORT_1.md (synthesis evidence)
- `hermes-chatgpt-mcp/hermes_chatgpt_mcp/schemas.py` (current MCP schemas)
- `hermes-chatgpt-mcp/hermes_chatgpt_mcp/command.py` (current adapter pattern)
- `hermes-agent/hermes_cli/kanban_db.py` (Hermes Kanban core)
- `hermes-agent/plugins/kanban/dashboard/plugin_api.py` (dashboard API)
- `hermes-agent/tools/registry.py` (native tool registry)

---

*End of MCP Topology ADR Draft*