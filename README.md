# hermes-chatgpt-mcp

`hermes-chatgpt-mcp` is an authenticated remote MCP facade for the canonical
Hermes Kanban service. It keeps the query adapter read-only, discovers an
explicit service-authorized set of Hermes boards, and exposes one narrowly
scoped command, `create_task`, through Hermes'
`hermes_cli.kanban_db.create_task` API.

## v0.3 scope

The public surface is seven READ tools plus one WRITE tool:

- READ: `list_boards`, `get_board`, `list_tasks`, `get_task`,
  `get_task_graph`, `get_dispatch`, `get_activity`;
- WRITE: `create_task` only.

There is still no update, delete, claim, assign-after-creation, move, start,
complete, close, review, approve, reject, retry, dispatch mutation, import, or
sync-back capability. Hermes remains the semantic authority for boards, task
status, links, scheduler state, outcomes, and audit activity. v0.3 is still
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
    ├── board resolver: canonical Hermes discovery + service allowlists
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
- The service user must be able to read every board in the configured read
  allowlist.
- The OCI service also needs write access only to the configured create-board
  directories for Hermes' canonical command connection and to its private
  OAuth state directory.

## Configuration

Copy [`.env.example`](.env.example) to a 0600 runtime environment file. At
minimum set:

```text
HERMES_AGENT_ROOT=/home/ubuntu/hermes-agent
HERMES_KANBAN_HOME=/home/ubuntu/.hermes
HERMES_KANBAN_BOARD=codex_app_server
MCP_KANBAN_READ_BOARDS=codex_app_server,dashboard
MCP_KANBAN_CREATE_BOARDS=codex_app_server,dashboard
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

`HERMES_KANBAN_BOARD` is the default used when `board` is omitted. The two
`MCP_KANBAN_*_BOARDS` values are deployment-level allowlists resolved through
Hermes' canonical `list_boards()` and `kanban_db_path()`. An explicit unknown
or unauthorized board never falls back to the default.

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

The v0.3 integration tests construct multiple temporary boards with Hermes'
`SCHEMA_SQL` and execute the real `kanban_db.create_task` command path; no
mocked task-creation implementation is used.

## MCP tools

READ tools:

- `list_boards`: bounded discovery of boards in the service read allowlist,
  including the resolved default and per-token create capability.
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

Scopes are separated:

- `hermes:read` is required by all seven query tools;
- `hermes:create` is required by `create_task`, and its grant also includes
  `hermes:read` because the MCP resource has a resource-wide read guard.
- `offline_access` is an OAuth protocol scope for refresh-token renewal; it
  grants no Hermes command capability.

A read-only token cannot create a card. The create tool is annotated
`readOnlyHint=false`, `destructiveHint=false` (additive write), and
`idempotentHint=true`; the required idempotency key makes safe retries return
the existing non-archived task instead of creating a duplicate.

Hermes currently has no per-principal board ACL model. Therefore the board
allowlists are service-level policy: every principal with `hermes:read` can
see the configured read boards, while `hermes:create` additionally enables
creation only on the configured create boards. A board outside the read
allowlist is reported as unavailable, so existence and authorization are not
distinguished to callers.

In ChatGPT, add a custom connector/MCP connection using:

```text
https://kanban.hermesinthenight.duckdns.org/mcp
```

Complete OAuth when ChatGPT opens the authorization page. Request both
`hermes:read` and `hermes:create` when the app should create cards; request
only `hermes:read` for a read-only connection. ChatGPT may use a frozen tool
snapshot for an existing app; reconnect or rescan the app after deployment so
`list_boards` and the current annotations are discovered. If OAuth asks for
the new create permission, approve it explicitly. An existing connection
authorized only for `hermes:read` cannot create until it is reauthorized with
`hermes:create`.

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

## Limitations of v0.3

- Board ACLs are service-level, not per-user/per-board. Hermes does not expose
  a canonical principal ACL, so the MCP cannot honestly claim finer isolation.
- Hermes' canonical board discovery is exposed only through the configured
  bounded allowlist; this service does not browse arbitrary filesystem paths.
- DCR clients and refresh-token rotation state persist, but authorization
  codes are intentionally ephemeral and access tokens expire normally.
- Existing v0.1 clients registered before the persistence rollout are not
  recoverable after the first restart and may need ChatGPT reauthorization.
- This is not a full write/control plane: `create_task` is the only write;
  comments, attachments, scheduler, notification, lifecycle, board
  administration, and task-editing mutations remain unavailable.
- The service depends on the installed Hermes command/query module and its
  SQLite schema; a Hermes upgrade should rerun reconnaissance and the live
  smoke before promotion.
- Public ChatGPT use still depends on the connector account accepting the
  configured OAuth callback and the external DNS/TLS path remaining available.
