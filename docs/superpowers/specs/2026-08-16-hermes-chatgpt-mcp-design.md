# Hermes ChatGPT MCP v0.1 Design

## Goal

Provide ChatGPT with a small, authenticated, remote MCP surface over the real
Hermes Kanban state while guaranteeing that every exposed operation is
read-only.

## Non-goals

- No task, board, dispatch, review, assignment, retry, or evidence mutation.
- No replacement scheduler or dependency engine.
- No dashboard UI and no general Hermes tool proxy.
- No direct exposure of SQLite, worker logs as arbitrary files, secrets, or
  attachment contents.

## Runtime choice

Use Python 3.11 with the Hermes Agent virtual environment as the runtime
dependency provider, `mcp==1.28.1`/FastMCP for current streamable HTTP, Pydantic
schemas, and Uvicorn for local/OCI execution. Python is selected because it can
import the canonical Hermes Python domain module without an RPC translation
layer or a second implementation of the Kanban model.

## Components

```text
hermes_chatgpt_mcp/config.py       bounded environment configuration
hermes_chatgpt_mcp/hermes.py       import/path resolution and read-only DB
hermes_chatgpt_mcp/adapter.py      canonical queries and safe projections
hermes_chatgpt_mcp/schemas.py      MCP input/output contracts
hermes_chatgpt_mcp/dispatch.py     deterministic read-only dispatch view
hermes_chatgpt_mcp/auth.py         OAuth 2.1 provider + bearer verifier
hermes_chatgpt_mcp/server.py       FastMCP registration and health route
```

The adapter owns no global connection. Each tool opens one bounded read-only
connection for the selected board and closes it in `finally`. The connection
uses the real Hermes database path, SQLite URI `mode=ro`, a bounded busy
timeout, `row_factory=sqlite3.Row`, and `PRAGMA query_only=ON`. It does not call
Hermes initialization/migration functions.

## MCP tools

Exactly six query tools are exposed:

| Tool | Purpose |
| --- | --- |
| `get_board` | Board metadata, canonical status counts, current-board marker, and bounded summary. |
| `list_tasks` | Bounded listing with board/status/assignee/tenant/session/archived/order filters. |
| `get_task` | One complete task projection, including latest run summary and direct links. |
| `get_task_graph` | Bounded root/parent/child graph traversal using canonical `task_links`. |
| `get_dispatch` | Deterministic queue/category/reason snapshot; never invokes dispatch. |
| `get_activity` | Events, comments, runs/outcomes, result/summary evidence, attachment metadata, and capped worker-log tail. |

Every tool is annotated `readOnlyHint=true`, `destructiveHint=false`, and
`openWorldHint=false`. Names, descriptions, schemas, and outputs contain no
mutating verbs. Input models forbid unknown fields and enforce finite lengths,
IDs, graph depth, log bytes, and result counts.

## Dispatch projection

Hermes raw states remain visible. The external projection is:

- `COMPLETED`: `done` or `archived`;
- `REVIEW`: `review`;
- `BLOCKED`: `blocked`, `triage`, dependency-gated `todo`, or a task whose
  current canonical state contains an explicit blocking reason;
- `READY`: `ready` with no active claim and a usable assignment.

`running` is returned as the raw execution state and in the separate running
collection; it is never misrepresented as a newly dispatchable task. Reasons
are generated from explicit canonical fields and links only, e.g. active run,
missing assignee, unresolved parent, block kind, failure counter, or completed
state. No status is rewritten to make the projection look cleaner.

## Authentication

The service is a protected resource with scope `hermes:read`. It publishes
OAuth authorization-server metadata and protected-resource metadata, accepts
dynamic public-client registration, requires authorization-code + PKCE S256,
and validates signed bearer tokens for issuer, resource/audience, expiration,
client, and scope. The configured login credential and HMAC signing key are
loaded only from the environment/secret file.

The MCP transport itself is `/mcp`. `/healthz` and OAuth discovery endpoints
are intentionally public so clients and systemd can discover/health-check the
service; tool calls are not.

## Error behavior

- Invalid inputs are rejected by the MCP/Pydantic schema with a bounded error.
- Unknown board/task IDs return a stable not-found error.
- Missing/unreadable/corrupt databases return a generic adapter error without
  filesystem paths or tracebacks in the client response.
- Unexpected errors are logged with a request correlation id but return only a
  generic error message.
- Tool results never include auth tokens, environment values, absolute
  attachment paths, or arbitrary filesystem data.

## Testing strategy

1. Unit tests prove path validation, read-only connection setup, serialization,
   graph traversal, dispatch reasons, log/attachment caps, and OAuth token/PKCE
   behavior.
2. A Hermes-schema fixture uses `hermes_cli.kanban_db.SCHEMA_SQL`, Hermes
   dataclasses, and representative tasks/runs/events/links.
3. MCP contract tests call initialization and all six tools through the real
   FastMCP ASGI app, including invalid arguments and missing IDs.
4. A read-only invariant hashes the fixture database and all sidecars before
   and after every tool call; hashes must be equal. It also attempts a write on
   the adapter connection and expects SQLite to reject it.
5. A live smoke opens the current OCI board using `mode=ro`, verifies
   `query_only`, calls the adapter queries, and records a before/after state
   fingerprint where no concurrent external change is observed.

## Deployment

The service binds to loopback under systemd. OpenResty terminates HTTPS on the
existing Kanban hostname and forwards only the MCP/OAuth/health paths to the
new loopback port. The deployment script installs a mode-600 env file without
printing values, validates the systemd unit and OpenResty configuration, and
performs authenticated/unauthenticated probes. No Hermes service is replaced or
reconfigured.

## Gate A decision

The design passes canonicality, isolation, read-only, stability, deployment,
and testability checks. No Hermes source change is necessary for v0.1.

