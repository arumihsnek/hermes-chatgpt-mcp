# hermes-chatgpt-mcp

`hermes-chatgpt-mcp` is an authenticated remote MCP facade for the canonical
Hermes Kanban service. It keeps the query adapter read-only, discovers all
active canonical Hermes boards for reading, and exposes one narrowly scoped
command, `create_task`, through Hermes'
`hermes_cli.kanban_db.create_task` API.

## v0.4 scope

The public surface is seven READ tools plus one WRITE tool:

- READ: `list_boards`, `get_board`, `list_tasks`, `get_task`,
  `get_task_graph`, `get_dispatch`, `get_activity`;
- WRITE: `create_task` only.

Read access is global to the active canonical boards. A write authorization is
bound to exactly one selected board; refresh preserves that board and OAuth
revocation invalidates the whole grant. There is still no update, delete, claim, assign-after-creation, move, start,
complete, close, review, approve, reject, retry, dispatch mutation, import, or
sync-back capability. Hermes remains the semantic authority for boards, task
status, links, scheduler state, outcomes, and audit activity. v0.4 is still
a minimal management surface, not a full Kanban controller.

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
    ├── OAuth grant: read all boards or write exactly one selected board
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

READ tools:

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

WRITE tool:

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

## Authentication and ChatGPT connection

The remote service requires a bearer token for `/mcp`; anonymous requests
receive `401`. OAuth uses public-client registration, authorization code, PKCE
S256, short-lived signed access tokens, rotated refresh tokens,
issuer/audience/expiry/scope validation, and a private login credential
supplied only through the environment file. The service advertises `none` as
its token endpoint authentication method and does not claim support for client
secrets.

Scopes and board grants are separate:

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

## Limitations of v0.4

- Board reads are intentionally global to the configured Hermes resource owner;
  this is not a per-user ACL model.
- A write grant covers exactly one board. Board administration and tenant
  creation are not exposed.
- DCR clients, refresh-token rotation state, and revoked grant IDs persist;
  authorization codes remain intentionally ephemeral.
- This is not a full write/control plane: `create_task` is the only write;
  comments, attachments, scheduler, notification, lifecycle, board
  administration, and task-editing mutations remain unavailable.
- The service depends on the installed Hermes command/query module and its
  SQLite schema; a Hermes upgrade should rerun reconnaissance and the live
  smoke before promotion.
- Public ChatGPT use still depends on the connector account accepting the
  configured OAuth callback and the external DNS/TLS path remaining available.
