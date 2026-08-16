# Hermes ChatGPT MCP v0.3 Multi-Board Design

**Date:** 2026-08-16  
**Status:** Accepted for implementation under the v0.3 mission

## Goal

Make real Hermes multi-board discovery, board selection, authorization, and
verification observable from ChatGPT while preserving the v0.2 Query/Command
boundary and exposing no new lifecycle controller operations.

## Reconnaissance baseline

The integration repository is `/home/ubuntu/code/hermes-chatgpt-mcp` on
`master` at `bbdd93ce2a24b501aeb23763ce0aa123960730e2`. The deployed systemd
service uses that checkout as its working directory. Its process started at
16:03:14 UTC, immediately after code commit `700ba8a` and before the later
documentation-only commit `bbdd93c`; therefore `700ba8a` is the deployed
v0.2 runtime code and `bbdd93c` is the current repository tip.

The canonical Hermes source is the dirty but pre-existing checkout
`/home/ubuntu/hermes-agent`, currently exposing
`hermes_cli.kanban_db` from that source tree. No Hermes files are changed by
this design.

Hermes v0.20.1 has a real board model:

- `kanban_home()` resolves the shared Hermes root using
  `HERMES_KANBAN_HOME` and the normal Hermes root fallback.
- `list_boards(include_archived=False)` is the canonical board discovery API.
  It always includes the legacy `default` board, then scans named board
  directories containing `board.json` or `kanban.db`.
- `read_board_metadata()` is the canonical metadata projection. Its result
  also contains `db_path`, which is intentionally not exposed externally.
- `board_exists()` and `kanban_db_path(board=...)` are canonical existence and
  path resolution helpers.
- Named boards have independent `kanban.db` files and metadata. The legacy
  `default` database remains at `<Hermes root>/kanban.db`.
- `get_current_board()` resolves the Hermes active board from scoped override,
  `HERMES_KANBAN_BOARD`, the persisted current-board file, and finally
  `default`.

The live Hermes root currently contains multiple named boards. The controlled
v0.3 deployment policy will expose `codex_app_server` and `dashboard` first;
both have real independent databases. The policy is explicit so a newly
created local board is not silently exposed to ChatGPT.

Hermes has no board/principal ACL model. Its `tenant` and `session_id` fields
are task metadata/filter fields, not access-control claims. The current OAuth
implementation also issues tokens with the same configured login identity and
does not carry a board ACL. v0.3 therefore implements service-level board
allowlists, reports them honestly, and does not claim per-user board
authorization.

## Architecture

```text
ChatGPT
   | OAuth principal + hermes:read / hermes:create
   v
MCP server
   | BoardResolver: canonical discovery + service allowlists
   +-----------------------------+
   |                             |
   v                             v
authorized BoardHandle       authorized BoardHandle
   |                             |
   | READ                         | CREATE
   v                             v
query adapter                 HermesCreateAdapter
   |                             |
SQLite mode=ro                 Hermes canonical
PRAGMA query_only=ON          kanban_db.create_task()
   |                             |
   +------------- Hermes board DB -------------+
```

The resolver returns an immutable board handle containing only the selected
slug, safe metadata, and a validated database path. A request with an omitted
board resolves to the configured default; a supplied board is resolved
exactly. Failure never falls back to the default.

Each selected board gets a query adapter bound to its own read-only store and,
for creation, a separate command adapter bound to the same canonical board
path. The query connection never calls Hermes' writable `connect()` or
`connect_closing()` helpers. The command path never performs SQL itself.

## Board authorization policy

The service adds two configuration values:

- `MCP_KANBAN_READ_BOARDS`: comma-separated canonical slugs. An omitted value
  fails safe to only the configured default board; it never enumerates every
  Hermes board by accident.
- `MCP_KANBAN_CREATE_BOARDS`: comma-separated canonical slugs. An omitted
  value means only the configured default board is creatable.

The create set must be a subset of the read set after resolution. OCI uses an
explicit read/create allowlist containing `codex_app_server,dashboard`.
systemd grants write access only to those two named board directories and the
OAuth state directory. Read access remains restricted by the resolver, even
though the process can technically read the Hermes root.

`list_boards` returns only boards in the read set. It reports
`capabilities.create=true` only when the current token has `hermes:create` and
the board is in the create set. A board outside the read set is omitted; an
unknown or non-readable explicit slug returns the same `BOARD_NOT_FOUND`
shape to avoid an existence leak. A readable but non-creatable board returns
`BOARD_NOT_ALLOWED` for a create request.

This is service-level authorization. Per-principal/per-board ACLs remain
`NOT_PROVEN` because Hermes and this OAuth deployment do not provide them.

## `list_boards` contract

The new tool has no request parameters. It uses Hermes'
`list_boards(include_archived=False)` and returns a bounded array of:

```json
{
  "slug": "codex_app_server",
  "name": "Codex Runtime",
  "description": "",
  "project_id": null,
  "created_at": 1786882346,
  "is_default": false,
  "task_counts": {"blocked": 2, "done": 9, "running": 1},
  "capabilities": {
    "read": true,
    "create": true
  }
}
```

The actual schema uses strict Pydantic models, bounded descriptions and a
bounded board count. It omits Hermes' physical `db_path`, `default_workdir`,
and other path-like metadata. Counts come from canonical `board_stats()` over
the same read-only query boundary used by `get_board`.

## Default and explicit board semantics

| Request | Resolution |
|---|---|
| `board` omitted | configured `HERMES_KANBAN_BOARD`; otherwise Hermes `get_current_board()`; startup fails if that default is not readable |
| `board=A` | canonical board `A`, only if discovered and readable |
| `board=unknown` | `BOARD_NOT_FOUND`; no default fallback |
| `create_task(board=A)` | first require `hermes:create`, then resolve `A` against the create allowlist, then invoke the canonical command |
| `create_task(board=B)` | independently resolves `B`; it cannot reuse A's store or current-board state |

The integration rejects an ambient `HERMES_KANBAN_DB` override because Hermes
would otherwise ignore an explicit board argument and route multiple slugs to
one physical database.

## Creation and retry safety

`create_task` remains a thin call to Hermes `kanban_db.create_task` with
`board=<resolved slug>`, `created_by=chatgpt_mcp`, and the existing safe input
subset. The v0.3 public schema requires `idempotency_key`; this makes an
automatic ChatGPT retry explicit rather than allowing an ambiguous duplicate.
The command adapter serializes creation per board in this single-instance
service before entering Hermes' canonical operation. Hermes' own idempotency
lookup remains authoritative; no MCP-side INSERT/UPDATE/DELETE is added.

Parent IDs are resolved inside the selected board database, so a parent from a
different board is naturally rejected by Hermes and cannot create a cross-board
link. The command response includes the selected board and canonical task
fields, allowing ChatGPT to verify the result with the read tools.

## Error model

Tool errors use a stable JSON object in the MCP error text:

```json
{"code":"BOARD_NOT_FOUND","message":"requested board is unavailable"}
```

The public codes are:

- `BOARD_NOT_FOUND`: unknown or not-readable board, deliberately
  indistinguishable;
- `BOARD_NOT_ALLOWED`: readable board is outside the create allowlist;
- `SCOPE_REQUIRED`: the token lacks `hermes:create`;
- `TASK_NOT_FOUND`: task ID is absent in the selected board;
- `CONFLICT`: canonical command rejected a conflicting request;
- `IDEMPOTENCY_CONFLICT`: reserved for a future canonical conflict response;
- `BACKEND_ERROR`: sanitized canonical/storage failure.

No SQL, filesystem path, traceback, token, or secret is returned.

## Management reconnaissance and v0.3 decision

Hermes provides canonical functions/CLI paths for many mutations, but most are
controller or recovery operations. The initial v0.3 surface intentionally
does not expose them:

| Operation | Canonical Hermes API | Invariants centralized | MCP decision | Scope | Risk |
|---|---|---:|---|---|---|
| discover boards | `list_boards`, `read_board_metadata` | yes | expose as `list_boards` | `hermes:read` | low |
| create task | `create_task` / `kanban create` | yes | keep, board-bound | `hermes:create` + read | medium |
| append comment | `add_comment` / `kanban comment` | yes, event `commented` | do not expose yet; candidate next increment | new append scope | low/medium |
| attach evidence | `add_attachment` / `kanban attach` | yes | do not expose; local file/path handling needs a separate contract | new append scope | medium |
| edit metadata | `specify_triage_task`, `set_model_override`, `set_reasoning_effort`, `set_workspace_path`, `set_branch_name` | yes, but field-specific | do not expose; not one safe generic update | management | medium/high |
| assign/reassign | `assign_task`, `reassign_task` | yes | do not expose; ownership/reclaim semantics | management | high |
| dependencies | `link_tasks`, `unlink_tasks` | yes | do not expose; graph mutation needs explicit contract | management | high |
| archive/delete board/task | `archive_task`, `delete_task`, `remove_board` | yes | do not expose; destructive | admin | critical |
| lifecycle | `block_task`, `schedule_task`, `promote_task`, `request_review`, `request_changes`, `reopen_review_task`, `complete_task`, `claim_task`, `dispatch_once` | yes | do not expose; controller/worker ownership | lifecycle | critical |
| board administration | `create_board`, `write_board_metadata`, `set_current_board`, `remove_board` | yes | do not expose; requires a future admin scope | `hermes:admin` | critical |

`get_capabilities` is not added. MCP `tools/list`, `list_boards` capabilities,
and the OAuth metadata already describe the active surface without another
tool that could drift from registration.

## Tenant, project, and session semantics

- `board` selects the physical Hermes queue/database and is the isolation
  boundary for tasks, links, events, runs, and dispatch state.
- `tenant` is an optional task column and an exact filter in Hermes
  `list_tasks`; it is not an authorization boundary.
- `session_id` records the originating Hermes agent/chat session when one is
  propagated via `HERMES_SESSION_ID`; it is also only an exact task filter.
- `project_id` is board metadata/task routing context for deterministic
  project workspaces. It is not a user or board ACL.

The MCP continues to expose `tenant` and `session_id` only as the existing
canonical task fields/filters and never treats either as a substitute for
OAuth board authorization.

## Verification plan

Tests will use two isolated fixture boards and the real Hermes
`hermes_cli.kanban_db` implementation:

1. discover both boards through canonical `list_boards`;
2. verify omitted/default, explicit A, explicit B, malformed, unknown, and
   no-fallback behavior;
3. verify all six existing reads are board-bound and cannot see the other
   board;
4. create one identifiable card in A and one in B through the same canonical
   command adapter used by MCP;
5. verify task, event, dispatch, idempotency, and state fingerprints for both
   boards;
6. verify OAuth read/create scope isolation and per-service board allowlists;
7. run the public OCI smoke against A and B, then clean only via canonical
   Hermes test cleanup APIs.

The existing v0.2 36-test suite remains a required regression gate. No real
board is changed until the isolated fixture and local integration tests pass.
