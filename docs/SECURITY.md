# Security boundary

## External surface

The public surface is the exact `/mcp` endpoint plus the OAuth discovery,
registration, authorization, token, and `/healthz` paths. OpenResty forwards
only those paths to loopback port 8789. The existing HermesKanban `/` route,
database files, and internal Hermes ports remain separate.

## Authentication and scopes

All MCP requests require a bearer token validated for issuer, audience,
expiry, signature, and `hermes:read`. OAuth registration accepts public
`none` clients, exact registered HTTPS redirect URIs (or localhost HTTP for
development), authorization code, PKCE S256, and only the supported scopes:

- `hermes:read` — seven query tools, including bounded `list_boards`;
- `hermes:create` — `create_task`, always granted together with
  `hermes:read`.
- `offline_access` — OAuth refresh-token renewal only; it is not a Hermes
  authorization scope.

The `scope` returned by DCR is the client's default scope metadata, not a
maximum permission grant. During `/oauth/authorize`, the resource owner may
explicitly approve any scope advertised by this authorization server. The
issued token still contains only the scopes requested and approved in that
authorization. A token containing only `hermes:read` remains unable to call
`create_task`.

The `create_task` handler performs an additional scope check. A valid
read-only token therefore cannot reach the command adapter. Login comparisons
are constant-time and failures are generic. No client secret is accepted.

## Query/command defense in depth

- `ReadOnlyHermesStore` is the only query storage boundary and uses SQLite URI
  `mode=ro` plus immediate `PRAGMA query_only=ON`.
- The query adapter never calls Hermes `connect`, `init_db`, `write_txn`,
  `create_task`, dispatch, or other mutators.
- `HermesCreateAdapter` is a separate class with one public method and calls
  only Hermes' canonical `kanban_db.create_task`; this repository contains no
  task-table write SQL.
- The MCP tool allowlist contains exactly eight tools: seven read tools and
  one create tool. No update/delete/claim/
  assign/move/start/complete/review/approve/reject/retry/import/sync tool is
  registered.
- Read tools are annotated `readOnlyHint=true`, `destructiveHint=false`, and
  `idempotentHint=true`.
- `create_task` is annotated `readOnlyHint=false`, `destructiveHint=false`
  (additive), and `idempotentHint=true`; its idempotency key is mandatory.
- `MCP_KANBAN_READ_BOARDS` and `MCP_KANBAN_CREATE_BOARDS` are deployment-level
  allowlists. Hermes has no per-principal board ACL, so this is not presented
  as user-specific authorization. Read-authorized boards are discoverable;
  create capability additionally depends on the OAuth token's
  `hermes:create` scope. Boards outside the read allowlist are intentionally
  indistinguishable from unknown boards.
- Strict Pydantic schemas reject unknown fields and bound IDs, title/body
  size, parent count, priority, and all list/graph/activity limits.
- Tests compare fixture state before/after every query operation and verify
  that denied/invalid creation calls do not add tasks. Multi-board tests use
  real Hermes fixture databases to prove A/B routing, idempotency, event
  creation, cross-board task isolation, and no fallback.

## OAuth persistence

The service persists only what must survive restart:

- DCR client metadata;
- hashes of active refresh tokens and their client/scope/expiry records.

Access tokens are signed self-contained JWT-like bearer values and are not
stored. Authorization codes are short-lived one-time values and remain
in-memory. Refresh tokens are rotated and the old hash is removed before the
new hash is persisted. The state file is written atomically with mode `0600`
inside a systemd-owned `0700` directory. Passwords, signing keys, and raw
refresh tokens are never written to Git or logs.

If the state file exists with broad permissions or an invalid structure, the
service fails closed instead of silently discarding client registrations.

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
restricted address families, and explicit write paths for only the configured
create-board directories (currently
`codex_app_server` and `dashboard`) and OAuth state directory. The service
binds to loopback; TLS is terminated by the existing OpenResty edge. The
deployment does not expose other Hermes services.
