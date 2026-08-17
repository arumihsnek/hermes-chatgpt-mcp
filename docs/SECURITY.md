# Security boundary

## External surface

The stable public surface is the exact `/mcp` endpoint plus the OAuth
discovery, registration, authorization, token, and `/healthz` paths. Stable
OpenResty forwards only those paths to loopback port 8789. The beta surface
uses the separate `kanban-beta.hermesinthenight.duckdns.org` hostname and
loopback port 8791 with its own include and service. The existing HermesKanban
`/` route, database files, and internal Hermes ports remain separate. Beta
DNS/TLS/OCI success is pending and is not asserted here.

## Stable authentication and scopes

On the stable surface, all MCP requests require a bearer token validated for
issuer, audience, expiry, signature, and `hermes:read`. Stable OAuth
registration accepts public `none` clients, exact registered HTTPS redirect
URIs (or localhost HTTP for development), authorization code, PKCE S256, and
only the supported scopes:

- `hermes:read` — seven query tools, including bounded `list_boards`;
- `hermes:create` — `create_task`, always granted together with
  `hermes:read`.
- `offline_access` — OAuth refresh-token renewal only; it is not a Hermes
  authorization scope.

`hermes:read` is global to all active canonical boards. The `scope` returned by
DCR is the client's default scope metadata, not a maximum permission grant.
During `/oauth/authorize`, the resource owner chooses either read-only access
to all boards or read plus write access to exactly one selected board. The
issued token contains only the approved scopes and, for a write grant, signed
`board` and `board_access=write` claims. A token containing only `hermes:read`
remains unable to call `create_task`.

The stable `create_task` handler performs an additional scope check. A valid
read-only token therefore cannot reach the command adapter. Login comparisons
are constant-time and failures are generic. No client secret is accepted.

## Beta surface and board grants

Beta is selected explicitly by `MCP_SURFACE=beta`; the stable default keeps
exactly eight tools and its three supported scopes. Beta has exactly eleven
tools and five supported scopes:

| Tool class | Tools | Scope and board rule |
| --- | --- | --- |
| Read | `list_boards`, `get_board`, `list_tasks`, `get_task`, `get_task_graph`, `get_dispatch`, `get_activity` | `hermes:read`; global active-board reads; SQLite `mode=ro` and `PRAGMA query_only=ON` |
| Task creation | `create_task` | `hermes:create` plus one selected board with `board_access=write` |
| Board creation | `create_board` | `hermes:board:create` plus `MCP_BOARD_CREATE_ENABLED=1`; global grant with no selected-board claim |
| Card management | `add_comment`, `assign_task` | `hermes:manage` plus one selected board with `board_access=write` |

`offline_access` is only the OAuth refresh protocol scope. `hermes:manage`
does not imply `hermes:create`, and a `hermes:board:create` grant cannot be
combined with a board-bound command grant. **create_board alone does not grant
task-write access** to the board it creates. A second authorization must select
that board for `hermes:create` or `hermes:manage` before a card, comment, or
assignment can be written.

The command resolver replaces an omitted command board with the signed grant
board and rejects an explicit different board as `BOARD_SESSION_MISMATCH`.
Thus, if a grant selected another board while Hermes' current default is
`seq66_looper`, explicitly requesting `seq66_looper` is an expected grant
mismatch, not a fallback or a missing-board diagnosis. `create_board` does not
change Hermes' current/default board; a subsequent `list_boards` call reports
the unchanged default and the new named board separately.

The beta command boundary is canonical and narrow: board creation calls
Hermes `create_board`; comment creation calls `add_comment` and reloads the
comment; assignment calls `assign_task` and reloads the task. Query and command
connections are separate. The public beta surface has no tenant administration,
delete/archive/rename/lifecycle/controller/import/sync operation, or arbitrary
task update. A task `tenant` value is metadata, not an ACL.

Beta DCR metadata, refresh-grant records, revoked-grant identifiers, and OAuth
state live in `/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json`; stable uses
`/var/lib/hermes-chatgpt-mcp/oauth-state.json`. The signing keys and private
environment files are also separate. Authorization codes remain ephemeral.

## Query/command defense in depth

The read/command separation applies to both surfaces. The exact eight-tool
allowlist and single-mutator statements below are stable-only.

- `ReadOnlyHermesStore` is the only query storage boundary and uses SQLite URI
  `mode=ro` plus immediate `PRAGMA query_only=ON`.
- The query adapter never calls Hermes `connect`, `init_db`, `write_txn`,
  `create_task`, dispatch, or other mutators.
- `HermesCreateAdapter` is a separate class with one public method and calls
  only Hermes' canonical `kanban_db.create_task`; this repository contains no
  task-table write SQL.
- On the stable surface, the MCP tool allowlist contains exactly eight tools:
  seven read tools and one create tool. No update/delete/claim/
  assign/move/start/complete/review/approve/reject/retry/import/sync tool is
  registered.
- Read tools are annotated `readOnlyHint=true`, `destructiveHint=false`, and
  `idempotentHint=true`.
- `create_task` is annotated `readOnlyHint=false`, `destructiveHint=false`
  (additive), and `idempotentHint=true`; its idempotency key is mandatory.
- `MCP_KANBAN_READ_BOARDS` and `MCP_KANBAN_CREATE_BOARDS` remain optional
  deployment caps. When omitted, all active canonical boards are readable and
  eligible for a write grant. They are not user ACLs. For stable
  `create_task`, the effective write boundary is the OAuth grant's one selected
  board plus `hermes:create`.
- Strict Pydantic schemas reject unknown fields and bound IDs, title/body
  size, parent count, priority, and all list/graph/activity limits.
- Tests compare fixture state before/after every query operation and verify
  that denied/invalid creation calls do not add tasks. Multi-board tests use
  real Hermes fixture databases to prove A/B routing, idempotency, event
  creation, cross-board task isolation, and no fallback.

## OAuth persistence

The service persists only what must survive restart:

- DCR client metadata;
- hashes of active refresh tokens and their client/scope/expiry/board records;
- revoked OAuth grant identifiers.

Access tokens are signed self-contained JWT-like bearer values and are not
stored. Authorization codes are short-lived one-time values and remain
in-memory. Refresh tokens are rotated and the old hash is removed before the
new hash is persisted. The state file is written atomically with mode `0600`
inside a systemd-owned `0700` directory. Passwords, signing keys, and raw
refresh tokens are never written to Git or logs.

If the state file exists with broad permissions or an invalid structure, the
service fails closed instead of silently discarding client registrations.

## OAuth grant revocation

`POST /oauth/revoke` accepts an access or refresh token and invalidates the
associated grant. Revocation removes all refresh-token records for the grant
and makes signed access tokens fail validation immediately through their
persisted grant identifier. The endpoint returns no token-state information.

## Temporary OAuth diagnostics

For the 2026-08-16 scope-loss experiment, the service can run with
`MCP_OAUTH_DIAGNOSTICS=1`. The diagnostic logger is disabled by default and
allows only known scope names, bounded protocol status fields, redirect
scheme/host/path, and short one-way fingerprints. It never records access
tokens, refresh tokens, authorization codes, PKCE values, credentials,
cookies, Authorization headers, or raw OAuth-state contents. Uvicorn access
logging is disabled in this diagnostic build so OAuth query strings are not
duplicated into the journal. Disable the flag and restart after the controlled
authorization has been observed.

## Data minimization and errors

Responses contain bounded IDs, titles, statuses, bodies, summaries, activity,
and safe attachment metadata. Stored filesystem paths, workspace paths,
credentials, environment-like metadata, and secret-like fields are removed or
redacted. Error responses are stable and do not expose SQL, stack traces, or
configuration values.

## Process and network controls

systemd runs as the unprivileged `ubuntu` user with `NoNewPrivileges`,
`ProtectSystem=full`, `ProtectHome=read-only`, private devices/temp space,
restricted address families, and write paths limited to canonical Hermes
named-board storage plus that service's own OAuth state directory. The legacy
root database is outside the stable and beta MCP write boundary. The query
adapter still uses SQLite `mode=ro` and `PRAGMA query_only=ON`; the
board-storage allowance is only for Hermes' canonical command connection. The
services bind to loopback; TLS is terminated by the corresponding OpenResty
edge. The deployment does not expose other Hermes services.
