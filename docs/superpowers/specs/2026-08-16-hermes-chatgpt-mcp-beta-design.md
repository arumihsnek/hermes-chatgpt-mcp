# Hermes ChatGPT MCP Beta: Board Administration and Card Management

**Status:** approved design for implementation

**Date:** 2026-08-16

## Goal

Create a beta MCP deployment that can create canonical Hermes boards and expose a small, auditable first slice of card management while leaving the existing production MCP endpoint, OAuth state, tool contract, and dogfooding workflow unchanged.

## Scope

The beta is a second service line, not a feature flag in the stable service. It uses the real Hermes canonical board home so it can be tested against real boards, but has its own process, public origin, OAuth state file, signing key, systemd unit, and deployment configuration.

The stable service remains the authority for the existing contract:

- `https://kanban.hermesinthenight.duckdns.org/mcp`
- loopback port `8789`
- seven read tools plus `create_task`
- existing `/var/lib/hermes-chatgpt-mcp/oauth-state.json`

The beta does not change that endpoint or its authorization semantics.

## Architecture

```text
ChatGPT beta session
        |
        | beta OAuth principal + scopes + optional one-board write grant
        v
beta MCP service (separate process, port 8791)
        |
        | strict board resolver
        +------------------------------+
        |                              |
        | READ                         | COMMAND
        v                              v
ReadOnlyHermesStore                narrow command adapters
SQLite mode=ro                     Hermes canonical functions only
PRAGMA query_only=ON               create_board/create_task/add_comment/assign_task
        |                              |
        +--------------+---------------+
                       v
              Hermes canonical board home
              /home/ubuntu/.hermes/kanban
```

The beta never imports a general-purpose mutator object into the query adapter and never issues task or board mutation SQL. Every write method has a dedicated adapter method and calls the corresponding Hermes function.

The preferred public beta origin is a separate hostname, `https://kanban-beta.hermesinthenight.duckdns.org`. A separate origin is required because OAuth issuer/resource metadata and the well-known endpoints must not collide with the stable service. The beta remains loopback-only until that origin is configured with valid TLS and proxying.

## Stable compatibility and concurrency

The stable service is not stopped, upgraded, or reconfigured as part of beta development. Both services may read the same canonical Hermes home. Command operations use Hermes' normal transaction and locking behavior; the beta does not introduce a second database or copy of board state.

`create_task` keeps the existing mandatory idempotency key. `create_board` retains Hermes' canonical idempotent slug behavior. The beta must test concurrent-safe retries against the canonical functions before being advertised for broad use.

Creating a board never changes Hermes' current/default board marker. The newly created board is discoverable immediately, but task-write access to it still requires an explicit OAuth authorization selecting that board.

## OAuth and board authorization

The beta supports these scopes:

- `hermes:read`: all active named-board read tools;
- `hermes:create`: `create_task`, together with `hermes:read` and one selected board grant;
- `hermes:manage`: card-management tools, together with `hermes:read` and one selected board grant;
- `hermes:board:create`: `create_board`, together with `hermes:read`; this is an administrative capability and is not implied by `hermes:create`;
- `offline_access`: refresh-token renewal only.

The existing one-board grant rule remains:

- reads are global to the named boards visible to the deployment;
- a command grant is bound to exactly one selected board;
- a command request for another board returns `BOARD_SESSION_MISMATCH`;
- a missing or invalid grant fails closed;
- changing the selected board requires a new authorization rather than a tool argument that silently changes session state.

`list_boards` reports per-board `read`, `create`, and `manage` capabilities for the current token. It also reports a bounded top-level `create_board` capability so ChatGPT can distinguish board administration from card writes. A board may be readable while both write capabilities are false.

The beta has a separate persisted OAuth state file and signing key. A beta client or grant is never silently looked up in the stable state file.

## Beta MCP surface

### Read

The stable seven read tools are carried forward unchanged:

```text
list_boards
get_board
list_tasks
get_task
get_task_graph
get_dispatch
get_activity
```

### Existing write

```text
create_task
```

It retains its current strict schema, canonical Hermes path, selected-board grant, and mandatory idempotency key.

### New board administration

```text
create_board
```

Input is deliberately limited to canonical safe metadata:

- `slug`: Hermes-valid board slug;
- `name`: bounded display name;
- `description`: bounded description;
- `icon`: bounded optional metadata;
- `color`: bounded optional metadata.

The beta does not expose `default_workdir`, arbitrary filesystem paths, archive flags, current-board switching, project routing, or a generic metadata dictionary. The adapter calls Hermes `create_board` and returns only safe board metadata plus the canonical slug. Existing-slug behavior follows Hermes and is surfaced explicitly as an idempotent existing-board result.

### New card management

```text
add_comment
assign_task
```

`add_comment` accepts a selected-board `task_id` and bounded `body`. The public caller cannot spoof an arbitrary author; the adapter records the fixed provenance `chatgpt_mcp` unless Hermes later provides a canonical authenticated actor identity suitable for this field.

`assign_task` accepts a selected-board `task_id` and one non-empty assignee value. It calls Hermes `assign_task`, preserving Hermes' refusal to reassign a currently running claimed task and its canonical `assigned` event. Unassignment, claim, dispatch, and lifecycle changes are not exposed in this slice.

All three new tools use `readOnlyHint=false`, `destructiveHint=false`, and explicit descriptions identifying their required scopes. They are not represented as a generic `update_task` dictionary.

## Deliberately excluded operations

The beta does not expose:

- board rename, archive, delete, or default switching;
- tenant creation or tenant administration;
- task delete, archive, title/body/priority arbitrary editing;
- dependency link/unlink;
- claim, start, dispatch, complete, review, approve, reject, retry, reopen, or cancel;
- model/provider/reasoning overrides;
- attachments or arbitrary evidence paths;
- import, sync-back, or controller operations.

Hermes' `tenant` remains task metadata, not an authorization or administrative object. No separate tenant registry is invented in the MCP.

## Error contract

New handlers use the existing structured MCP error envelope and stable codes:

- `SCOPE_REQUIRED`;
- `BOARD_WRITE_SELECTION_REQUIRED`;
- `BOARD_SESSION_MISMATCH`;
- `BOARD_NOT_FOUND`;
- `BOARD_NOT_ALLOWED`;
- `TASK_NOT_FOUND`;
- `CONFLICT` for Hermes validation/ownership rejection;
- `IDEMPOTENCY_CONFLICT` where a future canonical operation exposes a conflicting idempotency key;
- `BACKEND_ERROR` without stack traces or internal paths.

Unknown fields, malformed slugs/IDs, oversize strings, and unbounded arrays are rejected by strict schemas before command execution.

## File and module boundaries

The implementation stays in the beta worktree and is organized around the existing boundaries:

- `hermes_chatgpt_mcp/boards.py`: canonical discovery, exact resolution, per-board capability projection;
- `hermes_chatgpt_mcp/command.py`: existing create adapter plus dedicated board/comment/assignment adapters or narrowly scoped methods;
- `hermes_chatgpt_mcp/schemas.py`: strict beta request/result models;
- `hermes_chatgpt_mcp/server.py`: beta tool registration and scope enforcement;
- `hermes_chatgpt_mcp/auth.py` and `config.py`: beta-supported scopes and isolated persisted OAuth state;
- `deploy/systemd/hermes-chatgpt-mcp-beta.service`: independent service sandbox;
- `deploy/openresty/`: independent beta hostname locations;
- `tests/`: unit, contract, authorization, command-isolation, and real-fixture integration coverage.

No file under `/home/ubuntu/hermes-agent` is modified.

## Verification gates

Before beta exposure:

1. the complete stable suite still passes;
2. beta tools are exactly the documented surface;
3. all read operations preserve the read-only fingerprint invariant;
4. read-only tokens cannot invoke any beta write;
5. `hermes:create` cannot create boards;
6. `hermes:board:create` cannot manage or create tasks without their separate scopes;
7. a write grant for board A cannot mutate board B;
8. `create_board` creates one real canonical board and does not alter the default;
9. `add_comment` and `assign_task` create the canonical Hermes events;
10. a restart preserves beta DCR clients and refresh grants;
11. the beta endpoint is independently healthy and TLS/OAuth metadata point to the beta origin;
12. the stable endpoint remains healthy and unchanged.

The first live dogfood uses a clearly named test board created through the beta command path. No real production board is modified until the beta contract and authorization tests pass.
