# Security boundary

**Status:** V0.4 SECURITY CONTRACT (dated 2026-08-16; **SUPERSEDED for current runtime by the 2026-08-27 V4 stable cutover**). The v0.4 eight-tool allowlist and three-scope contract below remain the **v0.4 contract** for the `8791` beta deployment unit when it is resurrected. The V4 stable runtime uses a different topology (canary + 8789 override) and a **66-tool raw** surface today (reproducible 2026-08-28; the historical post-switch smoke `t_a47fd88f` reported **71**; the ChatGPT-visible / invocable surface is **11**, frozen by `t_01200e57`, and is **not** equal to raw `tools/list`). See [## V4 stable runtime (2026-08-27)](#v4-stable-runtime-2026-08-27) below for the current runtime security truth and [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](v4/CHECKPOINT-2026-08-27-V4-STABLE.md) for the reconciliation.

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

---

## V4 stable runtime (2026-08-27)

**This is the current runtime security truth.** The v0.4 security contract above remains the **v0.4 contract** for the `8791` beta deployment unit when it is resurrected. The V4 stable cutover uses the canary + 8789 override model; the public surface is **`https://kanban.hermesinthenight.duckdns.org`** forwarding via OpenResty to `127.0.0.1:8789` (the override-redirected stable). The pre-V4 `8791` beta (`kanban-beta.hermesinthenight.duckdns.org` → `127.0.0.1:8791`) is **dormant** in the V4 stable topology.

### V4 stable external surface (current)

| Public URL | Path | Forwarded to | Identity |
|------------|------|---------------|----------|
| `https://kanban.hermesinthenight.duckdns.org/mcp` | MCP | `127.0.0.1:8789` (override-redirected) | `4ae5060931a64741185c5c8deb3886a5901f21cc` / `beta` / `v4.wave0` |
| `https://kanban.hermesinthenight.duckdns.org/healthz` | healthz | `127.0.0.1:8789` (override-redirected) | same (with `x-v4-provenance`, `x-api-version`, `x-baseline-branch`, `x-baseline-mcp` headers) |
| `https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-authorization-server` | OAuth discovery | `127.0.0.1:8789` | DCR + PKCE S256 |
| `https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-protected-resource` | OAuth protected-resource | `127.0.0.1:8789` | resource metadata, scope list |
| `https://kanban.hermesinthenight.duckdns.org/oauth/...` | OAuth DCR/authorize/token/revoke | `127.0.0.1:8789` | standard OAuth 2.1 + DCR + PKCE S256 |
| (none) | canary `127.0.0.1:8792` | n/a — no public route | `4ae5060931a64741185c5c8deb3886a5901f21cc` / `beta` / `v4.wave0` (loopback only) |

### V4 stable authentication and scopes (current)

All MCP requests on the public origin require a bearer token validated for issuer, audience, expiry, signature, and `hermes:read`. OAuth registration accepts public `none` clients, exact registered HTTPS redirect URIs (or localhost HTTP for development), authorization code, PKCE S256, and the same scope vocabulary as v0.4 (`hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, `offline_access` for refresh tokens only). The current **proven** scope set is unchanged from the v0.4 contract; the V4 wave0 stable does **not** migrate to the fine-grained `hermes:task:read` / `hermes:task:create` / etc. PROPOSED scopes — those remain PROPOSED only and require their own connector release + E2E + dogfood chain before adoption.

### V4 stable tool surface (current)

| Surface | Tool count (raw) | Required (v4.wave0, all 6 present) | Source |
|---------|------------------|------------------------------------|--------|
| Public MCP `tools/list` (raw, reproducible 2026-08-28) | **66** | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` (all 6 present; subset of the 11-tool ChatGPT contract) | `t_f30cf660` parity investigation §3.1 (source enumeration at `4ae5060` + live readback) |
| Public MCP `tools/list` (historical post-switch smoke) | **71** | same | `t_a47fd88f` contract check #10, captured 2026-08-26 14:34 UTC; transient measurement, not reproducible against the same `4ae5060` today |
| ChatGPT-visible / invocable surface (frozen projection) | **11** | (the 6 v4.wave0 names are a strict subset) | `t_01200e57` ChatGPT session-compat contract; OpenAI's MCP connector filters `tools/list` and pins what it offers; **not equal to raw `tools/list`** |
| Canary `tools/list` (loopback only, raw) | **66** | same as public | `t_f30cf660` parity investigation §3.1 |
| Pre-V4 v0.4 stable allowlist | 8 | n/a (v0.4 contract) | v0.4 `SECURITY.md` above |
| Pre-V4 v0.4 beta allowlist | 11 | n/a (v0.4 contract) | v0.4 `SECURITY.md` above |

The 66-tool raw surface is the **post-Wave-0-to-4** surface (reproducible 2026-08-28 against the same `4ae5060` build); the historical 71 from the post-switch smoke is **not** a contract. Exposure is not validation, and `AVAILABLE_VALIDATED` requires real invocation evidence per tool. The **6 v4.wave0 required tools** are the only tools that MUST be present in every V4 wave; the **11-tool ChatGPT contract** (`t_01200e57`) is the only set ChatGPT can actually invoke, regardless of raw cardinality. See [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](v4/CHECKPOINT-2026-08-27-V4-STABLE.md) for the full reconciliation.

### V4 stable process and network controls (current)

The `hermes-chatgpt-mcp.service` (running the canary venv+WD via override) retains the v0.4 systemd hardening: `NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome=read-only`, private devices/temp space, restricted address families, write paths limited to canonical Hermes named-board storage plus the service's own OAuth state directory, and loopback bind with OpenResty TLS termination. The `hermes-chatgpt-mcp-canary.service` (port 8792) has the same hardening plus `ReadWritePaths=/home/ubuntu/.hermes/kanban/boards /var/lib/hermes-chatgpt-mcp-canary` and `PrivateDevices=yes`; it is bound to loopback and is **not** publicly routed.

### V4 stable OAuth state

`/var/lib/hermes-chatgpt-mcp/oauth-state.json` is **untouched** by the V4 stable cutover. Its mtime is `2026-08-27T20:40:40Z` (in the recovery window, not the cutover window). The cutover was a code cutover only: override.conf redirect + build.json write + one bounded restart. All DCR client metadata, refresh-grant records, revoked-grant identifiers, and signing keys are preserved across the cutover and would be preserved across a rollback. The signing key in `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` (mtime 2026-08-18, pre-promotion, **untouched**) is reused by the canary venv via the override drop-in's `EnvironmentFile` directive.

### V4 stable identity (durable binding)

- Connector: `4ae5060931a64741185c5c8deb3886a5901f21cc` (branch `v4-candidate-integration`)
- Phase-S source bundle: `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` (branch `release/source-bundle-phase-s`)
- Hermes Core MCP baseline: `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` (branch `v4/baseline-post-update-885e9ef`)
- Surface: `beta` (controller classifies as STABLE; `Kanban_Beta` discovery label is stale naming metadata)
- API version: `v4.wave0`
- Live raw MCP `tools/list` tool count (reproducible 2026-08-28): **66** distinct names — the historical post-switch smoke `t_a47fd88f` (2026-08-26 14:34 UTC) reported **71**; the 5-tool delta is transient / not reproducible against the same `4ae5060` today. The ChatGPT-visible / invocable surface is **11** (frozen by `t_01200e57`) and is **not** equal to raw `tools/list`. Full reconciliation: [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](v4/CHECKPOINT-2026-08-27-V4-STABLE.md) + `t_f30cf660` §3.1.
- v4.wave0 required tools (all 6 present, subset of the 11-tool ChatGPT contract): `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment`

### V4 stable rollback

The V4 stable rollback is **three reversible mutations only** (no credential rotation, no OAuth state rewrite, no OpenResty mutation, no schema migration):

1. **Delete the override drop-in** at `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` (SHA-256 `d8d87c59…1d90a`).
2. **Restore the prior-good `build.json`** from the in-place backup `/var/lib/hermes-chatgpt-mcp/build.json.pre-surface-rectification-20260826T103951Z.bak`.
3. **One bounded `systemctl restart hermes-chatgpt-mcp.service`**.

See [DEPLOYMENT.md §V4 stable runtime](DEPLOYMENT.md#v4-stable-runtime-2026-08-27) for the full rollback narrative and the byte-anchored R2 manifest pins.

### Authoritative references

- **[RELEASE-STABLE-V4.md](../RELEASE-STABLE-V4.md)** — durable release anchor.
- **[CHECKPOINT-2026-08-27-V4-STABLE.md](v4/CHECKPOINT-2026-08-27-V4-STABLE.md)** — full truth-sync checkpoint, including live readback, topology narrative, rollback path, residuals register, dogfood lessons.
- **[CURRENT_STATE.md](v4/CURRENT_STATE.md) §17** — V4 stable reconciliation summary.
- **[EVIDENCE_AND_OPEN_QUESTIONS.md](v4/EVIDENCE_AND_OPEN_QUESTIONS.md) §2 + §9** — `STILL_NOT_PROVEN` register + V4 stable residual register.
- **[STALE_DOCS.md](v4/STALE_DOCS.md)** — explicit classification of the v0.4 `8791` topology descriptions as **RETAIN / LINK; SUPERSEDE for current runtime**.

### Historical context (preserved)

The pre-V4 `8791` beta security contract (eleven-tool allowlist, five-scope contract, separate state directory and signing key) is **preserved unchanged** in the v0.4 section above. The v0.4 contract is the security contract to use when the `8791` beta is resurrected; it is **not** the current runtime security contract. The 2026-08-27 V4 stable cutover chose the canary + 8789 override model and reuses the **stable** v0.4 systemd hardening, OAuth scope vocabulary, OAuth DCR + PKCE S256 flow, refresh-rotation, and revocation semantics; the differences are **topology** (canary + 8789 override vs stable 8789 + beta 8791) and **raw tool count** (66 reproducible today vs 71 historical post-switch smoke vs 11 frozen ChatGPT contract; the v0.4 8/11-tool allowlists are preserved for the 8791 beta contract). See [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](v4/CHECKPOINT-2026-08-27-V4-STABLE.md) for the full reconciliation.
