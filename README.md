# hermes-chatgpt-mcp

`hermes-chatgpt-mcp` is an authenticated remote MCP facade for the canonical
Hermes Kanban service. Its stable surface keeps the query adapter read-only,
discovers all active canonical Hermes boards for reading, and exposes one
narrowly scoped command, `create_task`, through Hermes'
`hermes_cli.kanban_db.create_task` API.

## Stable v0.4 scope

The stable public surface is seven READ tools plus one WRITE tool:

- READ: `list_boards`, `get_board`, `list_tasks`, `get_task`,
  `get_task_graph`, `get_dispatch`, `get_activity`;
- WRITE: `create_task` only.

On the stable surface, read access is global to the active canonical boards. A
write authorization is bound to exactly one selected board; refresh preserves
that board and OAuth revocation invalidates the whole grant. There is still no
update, delete, claim, assign-after-creation, move, start,
complete, close, review, approve, reject, retry, dispatch mutation, import, or
sync-back capability. Hermes remains the semantic authority for boards, task
status, links, scheduler state, outcomes, and audit activity. v0.4 is still
a minimal management surface, not a full Kanban controller.

## Stable and beta endpoints

The stable and beta surfaces are separate MCP services and separate OAuth
resource servers. The stable endpoint is the configured
`https://kanban.hermesinthenight.duckdns.org/mcp` origin on loopback
`127.0.0.1:8789`. The beta endpoint is the configured
`https://kanban-beta.hermesinthenight.duckdns.org/mcp` origin on loopback
`127.0.0.1:8791`. The beta hostname has its own OpenResty include and does not
change the stable hostname's locations.

| Surface | Exact public tool set | Supported scopes | Command grant |
| --- | --- | --- | --- |
| Stable | eight tools: the seven read tools above plus `create_task` | `hermes:read`, `hermes:create`, `offline_access` | `create_task` needs `hermes:create` and one selected board with `board_access=write` |
| Beta | 51 canonical leaves (the `boards` routing container and aliases are excluded) | `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, `hermes:admin`, `offline_access` | normal task mutations use `hermes:manage`; destructive, runtime, and filesystem-sensitive actions require explicitly consented `hermes:admin` |

The stable default remains unchanged: it registers no beta tools and does not
advertise `hermes:manage` or `hermes:board:create`. Beta is selected explicitly
by `MCP_SURFACE=beta` and the beta entrypoint. A beta installation therefore
does not turn the stable endpoint into a beta endpoint.

## Architecture

```text
ChatGPT web
    │ OAuth 2.1 + PKCE, HTTPS
    ▼
OpenResty /mcp and OAuth paths
    │ loopback 127.0.0.1:8789
    ▼
hermes-chatgpt-mcp (systemd)
    ├── board resolver: canonical Hermes discovery + optional deployment caps
    ├── stable OAuth grant: read all boards or write exactly one selected board
    ├── query path: mode=ro + PRAGMA query_only=ON
    │       ▼
    │   Hermes hermes_cli.kanban_db query API
    │
    └── command path: HermesCreateAdapter
            ▼
        Hermes hermes_cli.kanban_db.create_task
            ▼
        Hermes Kanban SQLite/WAL state
```

The query and command paths use separate adapters and connections. The
command path calls Hermes' canonical operation; this repository never issues
an `INSERT INTO tasks`. The reconnaissance, command-path decision, and
rejected alternatives are recorded in
[`docs/architecture/HERMES-INTEGRATION.md`](docs/architecture/HERMES-INTEGRATION.md).

## Requirements

- Python 3.11.
- Hermes installed at `/home/ubuntu/hermes-agent`, or `HERMES_AGENT_ROOT`
  pointing to the real source tree.
- The service user must be able to read the canonical active board databases.
- The OCI service needs write access to the Hermes boards root for the
  canonical command connection and to its private OAuth state directory.

## Configuration

Copy [`.env.example`](.env.example) to a 0600 runtime environment file. At
minimum set:

```text
HERMES_AGENT_ROOT=/home/ubuntu/hermes-agent
HERMES_KANBAN_HOME=/home/ubuntu/.hermes
# Omit the following optional caps to use all active canonical boards:
# HERMES_KANBAN_BOARD=codex_app_server
# MCP_KANBAN_READ_BOARDS=codex_app_server,dashboard
# MCP_KANBAN_CREATE_BOARDS=codex_app_server,dashboard
MCP_PUBLIC_BASE_URL=https://kanban.hermesinthenight.duckdns.org
MCP_HOST=127.0.0.1
MCP_PORT=8789
MCP_OAUTH_USERNAME=chatgpt
MCP_OAUTH_PASSWORD=<random password, never commit>
MCP_OAUTH_SIGNING_KEY=<random signing key, never commit>
MCP_OAUTH_STATE_FILE=/var/lib/hermes-chatgpt-mcp/oauth-state.json
```

Remote origins must use HTTPS. Local development may use
`http://127.0.0.1:8789`. Input, graph, activity, OAuth-code, and token bounds
are configurable but fail closed when invalid. The production state file
contains DCR metadata and refresh-token hashes, never plaintext refresh tokens
or passwords.

## Local execution

```bash
cp .env.example .env
# Replace the secret placeholders in .env; do not commit it.
set -a; . ./.env; set +a
/home/ubuntu/hermes-agent/venv/bin/python -m hermes_chatgpt_mcp.server
```

The MCP endpoint is `/mcp`; liveness is `/healthz`. OAuth metadata is exposed
at `/.well-known/oauth-authorization-server`, and protected-resource metadata
at `/.well-known/oauth-protected-resource`.

When `HERMES_KANBAN_BOARD` is omitted, a read request without `board` follows
Hermes' current default dynamically. The optional `MCP_KANBAN_*_BOARDS` values
are deployment caps, not user permissions; when omitted, all active canonical
boards are readable and eligible for a write grant. An explicit unknown board
never falls back to the default. `create_task` additionally requires a
write-capable OAuth grant bound to that exact board.

## Tests and live proof

The suite includes unit, command-adapter, contract, OAuth persistence,
scope-isolation, multi-board A/B routing, integration-fixture, and
before/after read-only fingerprint tests:

```bash
/home/ubuntu/hermes-agent/venv/bin/python -m pytest -q
/home/ubuntu/hermes-agent/venv/bin/python -m compileall -q hermes_chatgpt_mcp tests scripts
```

The live read smoke is opt-in and requires an explicit board; it calls the six
task-scoped canonical read operations against the real Hermes installation and
checks DB/WAL/metadata fingerprints. Multi-board routing additionally uses the
MCP fixture/integration tests and the deployment checklist to exercise
`list_boards`, board A, and board B:

```bash
HERMES_LIVE_TEST=1 \
HERMES_AGENT_ROOT=/home/ubuntu/hermes-agent \
HERMES_KANBAN_HOME=/home/ubuntu/.hermes \
HERMES_KANBAN_BOARD=codex_app_server \
/home/ubuntu/hermes-agent/venv/bin/python scripts/live_smoke.py
```

The v0.4 integration tests construct multiple temporary boards with Hermes'
`SCHEMA_SQL` and execute the real `kanban_db.create_task` command path; no
mocked task-creation implementation is used.

After deployment, the endpoint-level A/B check is:

```bash
set -a; . /home/ubuntu/.hermes/hermes-chatgpt-mcp.env; set +a
HERMES_LIVE_TEST=1 \
/home/ubuntu/hermes-agent/venv/bin/python scripts/live_multiboard_smoke.py

# Only for the controlled one-card-per-board write proof:
HERMES_LIVE_TEST=1 HERMES_LIVE_WRITE_TEST=1 \
/home/ubuntu/hermes-agent/venv/bin/python scripts/live_multiboard_smoke.py
```

The write mode uses unique `[mcp-v04-smoke ...]` titles and cleans up through
Hermes' native archive/delete functions in a `finally` block. It is never an
MCP capability.

## MCP tools

Stable READ tools:

- `list_boards`: bounded discovery of all active named canonical boards and
  the single-board write capability of the token. Hermes' legacy root
  `default` database alias is intentionally not exposed as a board.
- `get_board`: selected board metadata and canonical status/assignee counts.
- `list_tasks`: bounded canonical task listing with status, assignee, tenant,
  session, archive, limit, and order filters.
- `get_task`: task body and canonical fields, direct parents/children, run
  summaries, and safe attachment metadata.
- `get_task_graph`: bounded root-centered parent/child graph with explicit
  truncation.
- `get_dispatch`: deterministic `READY`, `BLOCKED`, `REVIEW`, or `COMPLETED`
  projection with reasons and raw Hermes status.
- `get_activity`: bounded events/ledger, comments, runs/outcomes, worker-log
  tail, result/summary, and attachment metadata.

Stable WRITE tool:

- `create_task`: creates exactly one card through Hermes' canonical command
  operation. It accepts the selected board, title, body, parent task IDs,
  initial assignee, priority, tenant, session ID, triage flag, and a required
  idempotency key. Hermes supplies the task ID, canonical status, `created`
  event, parent links, notification inheritance, and `created_by=chatgpt_mcp`.

`acceptance_criteria` is not a Hermes task field; include it in `body`. The
create schema does not accept workspace paths, projects, model/provider
overrides, skills, retry policy, arbitrary initial statuses, or any operation
name. Unknown fields, invalid IDs, excessive payloads, missing parents, and
unsupported values are rejected before or during the canonical transaction.

### Beta board-management tools

The beta surface exposes the complete 51-leaf canonical Kanban action surface
(aliases and the `boards` routing container are not separate tools). The
original 11 tools remain unchanged; typed additions cover lifecycle,
dependency, attachment, dispatch, diagnostics, notification, worker-context,
recovery, and board-administration actions. `hermes:admin` is an explicit
elevated scope for runtime, destructive, and filesystem-sensitive leaves.

| Tool | Required scope | Board binding | Canonical operation |
| --- | --- | --- | --- |
| `create_board` | `hermes:board:create` and the deployment flag `MCP_BOARD_CREATE_ENABLED=1` | Global; the request has no board-selection field and the grant has no board claim | `HermesBoardAdminAdapter` calls Hermes `create_board` and returns safe metadata |
| `add_comment` | `hermes:manage` | Exactly one selected board with `board_access=write` | `HermesCardManagementAdapter` calls Hermes `add_comment`, then reloads the comment |
| `assign_task` | `hermes:manage` | Exactly one selected board with `board_access=write` | `HermesCardManagementAdapter` calls Hermes `assign_task`, then reloads the task |

`create_task` remains available on beta with `hermes:create` and the same
one-board grant rule as stable. `hermes:manage` does not imply `hermes:create`.
`hermes:board:create` is a separate global board-creation scope. It never
implies `hermes:admin` or task/card writes. A grant that includes command scopes
(`hermes:create` / `hermes:manage`) must also carry the explicitly selected
board claim; `hermes:admin` may be consented separately for elevated
administration/runtime/filesystem/destructive leaves, while command writes
remain board-bound. **create_board alone does not grant task-write access** to
the new board. After creating a board, authorize a command grant for that board
before creating a card, comment, or assignment.

Every beta board-bound command is checked against the signed OAuth one-board
claim before an adapter is constructed. The global `create_board` command is
the explicit exception: it uses a global `hermes:board:create` grant and has no
board claim. An omitted board on a board-bound command uses the board in that
grant. An explicit different board fails with `BOARD_SESSION_MISMATCH`; it does
not fall back to Hermes' current default.
For example, if a grant selected `other-board` while Hermes currently reports
`seq66_looper`, a request explicitly naming `seq66_looper` is expected to fail
with `BOARD_SESSION_MISMATCH`. That result means the selected OAuth board and
the requested board differ; it is not evidence that `seq66_looper` is missing.

`list_boards` is read-only and reports the current `default_board`, per-board
`is_default`, and beta command capabilities. `create_board` creates through
Hermes' canonical board API, does not select the board, and does not change
Hermes' current/default board. The new named board therefore appears in a
later `list_boards` response without becoming the default. Query adapters use
SQLite URI `mode=ro` plus `PRAGMA query_only=ON`; command adapters use separate
canonical Hermes connections. No SQL mutation is added here.

The beta public surface does not expose arbitrary shell, SQL, import, or sync
operations. All task and board mutations use strict typed envelopes and fixed
canonical Hermes entry points. A task's optional `tenant` remains metadata
passed to canonical `create_task`, not an authorization boundary.

## Authentication and ChatGPT connection

The remote service requires a bearer token for `/mcp`; anonymous requests
receive `401`. OAuth uses public-client registration, authorization code, PKCE
S256, short-lived signed access tokens, rotated refresh tokens,
issuer/audience/expiry/scope validation, and a private login credential
supplied only through the environment file. The service advertises `none` as
its token endpoint authentication method and does not claim support for client
secrets.

### Stable scopes and board grants

For the stable surface, scopes and board grants are separate:

- `hermes:read` is required by all seven query tools and reads every active
  canonical board;
- `hermes:create` is required by `create_task`, but it is never sufficient by
  itself: the OAuth grant must also contain exactly one selected board with
  `board_access=write`;
- `offline_access` is an OAuth protocol scope for refresh-token renewal; it
  grants no Hermes command capability.

A DCR registration's returned `scope` is the client's default scope metadata,
not a token grant. The OAuth consent page offers either read-only access to all
boards or read plus write access to one selected board. Existing tokens are
never upgraded silently; selecting another write board requires a new
authorization, and `/oauth/revoke` invalidates the grant immediately.

A read-only token cannot create a card. The create tool is annotated
`readOnlyHint=false`, `destructiveHint=false` (additive write), and
`idempotentHint=true`; the required idempotency key makes safe retries return
the existing non-archived task instead of creating a duplicate.

Hermes currently has no per-principal board ACL model. This v0.4 contract is
therefore intentionally resource-owner/session scoped: `hermes:read` permits
global reading, while a signed OAuth grant limits `hermes:create` to one
canonical board. The grant is not a replacement for a future multi-user
Hermes ACL service.

In ChatGPT, add a custom connector/MCP connection using:

```text
https://kanban.hermesinthenight.duckdns.org/mcp
```

Complete OAuth when ChatGPT opens the authorization page. The page lists all
active boards and offers read-only access to all of them or read+write access
to exactly one selected board. A read-only token can search/read every board;
`create_task` is available only on the selected write board. To change the
write board, revoke/reconnect the app and choose the new board. ChatGPT may use
a frozen tool snapshot for an existing app; reconnect or rescan after
deployment so the current OAuth metadata and tool annotations are discovered.

The callback must be the URI ChatGPT sends during dynamic registration; the
implementation accepts the documented
`https://chatgpt.com/connector/oauth/...` callback family through its exact
registered redirect URI. See OpenAI's current guidance on [ChatGPT developer
mode and MCP apps](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta),
[Apps in ChatGPT](https://help.openai.com/en/articles/11487775-apps-in-chatgpt),
and [MCP tool authorization fields](https://platform.openai.com/docs/api-reference/realtime-server-events/input_audio_buffer/committed?lang=node).

### Beta OAuth reauthorization

Add the beta URL as a separate ChatGPT connector, then complete a fresh
dynamic-registration, PKCE, and authorization flow against the beta origin.
Do not expect a stable connection to gain beta scopes: stable and beta have
separate DCR records, OAuth state files, signing keys, and refresh-grant
records. A restart preserves each service's own DCR and refresh state, while
authorization codes remain ephemeral. If ChatGPT shows an older tool snapshot,
reconnect or rescan the beta connector after the beta metadata is available.

For board management, first use a global `hermes:board:create` authorization
to create the named board. Verify it with `list_boards`; then reauthorize the
beta connector and select that board for a one-board `hermes:create` or
`hermes:manage` grant. Selecting a different write board always requires a
new authorization; a tool call cannot self-grant or move the board binding.

### Bounded beta dogfood prompt

Use this prompt only against a disposable test board and stop when the prompt
requires user authorization:

```text
Use the beta MCP connection for a bounded board-management dogfood.

1. Call list_boards and record the current default_board and the visible
   capability flags. Do not assume the current default is the board to test.
2. Choose a uniquely named, valid test-board slug using the current UTC time.
3. Call create_board once with that slug and a clearly test-only name.
4. Call list_boards again and verify that exactly one item has the new slug and
   that the current default_board has not changed.
5. Stop and tell the user to authorize/reconnect the beta connector and select
   the new board for a one-board command grant. Explain that create_board alone
   does not grant task-write access. Do not continue until that authorization
   is complete.
6. After authorization, create exactly one test card on the selected board
   with create_task and a unique idempotency key.
7. Add exactly one test comment to that card with add_comment.
8. assign it once with assign_task, then report the returned task and
   activity identities without printing credentials or token values.
```

This is a procedure for future controlled validation, not a claim that live
ChatGPT or beta DNS/TLS/OCI validation has completed; that validation is
pending.

## OCI deployment

The reproducible installer targets the existing machine boundary:

```bash
./scripts/install_oci.sh
```

It installs `hermes-chatgpt-mcp.service`, creates/updates the 0600 environment
file without printing its values, creates the private systemd state directory
for persisted OAuth state, binds only to loopback port 8789, validates the
active 1Panel OpenResty container configuration, reloads the existing
OpenResty hook, and checks `/healthz`. The existing TLS host keeps its
HermesKanban `/` route; only `/mcp`, OAuth metadata/auth/token, and `/healthz`
are proxied to this service. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for
restart, persistence, rollback, and verification.

```bash
sudo systemctl status hermes-chatgpt-mcp.service
sudo systemctl restart hermes-chatgpt-mcp.service
sudo journalctl -u hermes-chatgpt-mcp.service -f
./scripts/uninstall_oci.sh
```

The installer preserves the runtime environment and timestamped edge backups
during rollback. It never modifies Hermes source or Kanban rows itself.

### Beta deployment and rollback target

The beta deployment is prepared by running the candidate worktree's installer
with an exact beta commit:

```bash
./scripts/install_oci_beta.sh <exact-beta-commit>
```

The installer fails closed unless the candidate is the expected Git worktree at
that commit and clean. It installs only the beta unit and beta OpenResty
include, creates the beta state directory, and writes/preserves the private
beta environment file at `/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env`
with mode `0600`. It supplies beta-only settings for
`MCP_SURFACE=beta`, `MCP_BOARD_CREATE_ENABLED=1`, loopback port `8791`, the
beta public origin, and
`/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json`; credentials are never
printed. The stable environment and OAuth state remain separate.

Before mutation it validates the beta edge include. After installing the beta
unit it runs an OpenResty syntax check, enables and restarts only
`hermes-chatgpt-mcp-beta.service`, waits for `GET http://127.0.0.1:8791/healthz`
to return `{"status":"ok"}`, and reloads the existing OpenResty hook. These
are installer behaviors; this repository has not run the installer or claimed
live OCI, DNS, TLS, or ChatGPT success.

The installer has an automatic transactional rollback for a failed beta
installation: it restores the prior beta unit, include, edge configuration,
private environment, and service state, revalidates/restores the edge after a
reload attempt, and never restarts the stable unit. For a user-facing fallback,
keep the stable service as the rollback target and reconnect ChatGPT to the
stable endpoint; stable OAuth authorization is separate from beta OAuth
authorization. Treat deliberate beta disablement or removal as a separate,
change-controlled operator action after stable health is confirmed.

## Limitations of v0.4

- Board reads are intentionally global to the configured Hermes resource owner;
  this is not a per-user ACL model.
- On the stable surface, a write grant covers exactly one board. Board
  administration and tenant creation are not exposed.
- DCR clients, refresh-token rotation state, and revoked grant IDs persist;
  authorization codes remain intentionally ephemeral.
- On the stable surface, this is not a full write/control plane: `create_task`
  is the only write; comments, attachments, scheduler, notification,
  lifecycle, board administration, and task-editing mutations remain
  unavailable. Beta adds only the documented board-management tools.
- The service depends on the installed Hermes command/query module and its
  SQLite schema; a Hermes upgrade should rerun reconnaissance and the live
  smoke before promotion.
- Public ChatGPT use still depends on the connector account accepting the
  configured OAuth callback and the external DNS/TLS path remaining available.
