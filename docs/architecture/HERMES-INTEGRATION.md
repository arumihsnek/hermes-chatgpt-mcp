# Hermes integration reconnaissance

Status: architecture selected for MCP v0.1 (2026-08-16)

## Hermes repository

The canonical Hermes Agent source checkout is:

```text
/home/ubuntu/hermes-agent
```

The installed executable resolves to `/home/ubuntu/hermes-agent/venv/bin/hermes`
and reports Hermes Agent v0.20.1. The checkout was already dirty during
reconnaissance; its existing changes were preserved and no Hermes files were
modified by this project. The relevant Kanban kernel file
`hermes_cli/kanban_db.py` was inspected as the source of truth.

`/home/ubuntu/code/HermesKanban` is a separate companion WebUI. It imports
`hermes_cli.kanban_db`, which confirms the shared domain boundary, but its API
also exposes task creation, updates, deletion, dispatch, board changes, and
other mutations. It is therefore not a safe MCP adapter boundary.

## Canonical task model

`hermes_cli.kanban_db.Task` is the canonical task/card projection. The model
contains the stable identifiers and lifecycle fields needed by the integration:
`id`, `title`, `body`, `assignee`, `status`, priority, timestamps, workspace
metadata, claim/heartbeat data, result, failure counters, review/block fields,
and workflow routing fields.

Canonical statuses currently include:

```text
triage, todo, scheduled, ready, running, blocked, review, done, archived
```

The public read adapter preserves the canonical status instead of inventing a
second lifecycle. Its dispatch projection groups these states into the v0.1
external categories `READY`, `BLOCKED`, `REVIEW`, and `COMPLETED`, while also
returning the original Hermes status and a deterministic reason list.

## Canonical board implementation

Boards are implemented in `hermes_cli.kanban_db`:

- The default board uses `<Hermes root>/kanban.db` for backwards compatibility.
- Named boards use `<Hermes root>/kanban/boards/<slug>/kanban.db`.
- Board metadata is read from `board.json` under the board directory.
- The active board is selected by Hermes' existing resolution chain, including
  `HERMES_KANBAN_BOARD` and `<Hermes root>/kanban/current`.
- Slugs are validated by Hermes' lowercase alphanumeric/hyphen/underscore
  contract.

The live installation currently resolves its active board to
`codex_app_server`; the adapter accepts an explicit board slug so ChatGPT can
query a known board without changing Hermes' active-board selection.

## Canonical query API

Hermes provides pure query/model functions in `hermes_cli.kanban_db`, including:

- `get_task`, `list_tasks`, `board_stats`;
- `task_graph_contexts`, `parent_ids`, and `child_ids`;
- `list_comments`, `list_events`, `list_runs`, `latest_summary`;
- `read_worker_log`, `list_attachments`, `read_board_metadata`.

There is no separate read-only Kanban service API in the inspected Hermes
checkout. `kanban_db.connect()` is explicitly a writable initialization path:
it can create directories, enable WAL, run schema creation, and apply additive
migrations. The integration therefore opens the resolved database itself with
SQLite URI `mode=ro`, sets `PRAGMA query_only=ON`, and passes that connection to
the pure Hermes query/model functions. It never calls `kanban_db.connect()` or
`init_db()`.

The adapter uses Hermes dataclasses and query functions for domain fidelity;
its own code is limited to input bounds, read-only connection lifecycle,
recursive graph hydration, serialization, and dispatch presentation.

## Canonical scheduler/dispatch

The dispatcher lives in `hermes_cli.kanban_db.dispatch_once()` and the CLI
entry point is `hermes_cli/kanban.py`. The dispatcher owns claims, retries,
stale-worker reconciliation, dependency promotion, profile resolution, worker
spawning, and event emission. Those functions are intentionally not called by
the MCP adapter: even `dry_run` executes maintenance/reconciliation paths and
is not an acceptable read-only boundary.

`get_dispatch` is therefore a deterministic snapshot of the current canonical
state, not a second dispatcher. It reports raw status counts, running tasks,
and bounded per-task categories/reasons derived from canonical status,
dependency links, claims, assignment, failure fields, and run history. It does
not promote, claim, retry, reconcile, assign, or otherwise alter a task.

## Canonical evidence/activity source

Hermes stores activity in the same board database:

- `task_events` and `kanban_db.list_events()` are the lifecycle/event ledger
  available in v0.1.
- `task_runs` and `kanban_db.list_runs()` carry attempts, outcomes, errors,
  summaries, heartbeats, and worker metadata.
- `tasks.result` and the latest non-empty run summary are the available
  outcome/evidence fields.
- Worker log files are read through `kanban_db.read_worker_log()` with a
  strict tail-byte cap.
- Attachment metadata is available; v0.1 returns metadata only and never
  exposes stored filesystem paths or file contents.

Hermes does not expose a separate first-class evidence or ledger table in the
inspected schema, so `get_activity` labels these canonical sources explicitly
instead of pretending they are a new evidence system.

## Storage

Storage is SQLite with WAL sidecars on the OCI host. The live installation
contains the legacy default database at `/home/ubuntu/.hermes/kanban.db` and
named board databases under `/home/ubuntu/.hermes/kanban/boards/`.

The service resolves board paths through Hermes' `kanban_home()`/
`kanban_db_path()` path rules, but opens only existing database files in
read-only URI mode. Missing boards/databases fail closed with a sanitized
not-found/error response; the service never creates an empty board as a side
effect of a query.

## Existing HTTP/API

`plugins/kanban/dashboard/plugin_api.py` provides the existing dashboard HTTP
routes and useful serialization examples. It is not used as a backend because
the same router exposes mutating POST/PATCH/DELETE/dispatch routes and its
connection helper initializes the database through the writable Hermes path.

The integration exposes its own `/mcp` streamable HTTP endpoint and does not
proxy or mount the dashboard API.

## Authentication

Hermes' local/dashboard authentication and the host's shared cookie proxy are
browser-oriented infrastructure, not an OAuth resource-server contract for a
ChatGPT MCP client. The integration owns the MCP authorization boundary:

- OAuth 2.1 authorization-code flow with PKCE S256;
- dynamic registration for a public client using `token_endpoint_auth_method`
  `none`;
- protected-resource and authorization-server metadata;
- a configured local login credential, supplied only through a mode-600 env
  file/secret manager;
- signed short-lived bearer access tokens validated on every MCP request;
- required scope `hermes:read` and an audience/resource check.

The public TLS edge is OpenResty on the OCI host. v0.1 uses the existing
`kanban.hermesinthenight.duckdns.org` certificate and adds only a path-specific
proxy for `/mcp`, OAuth metadata/auth paths, and `/healthz`; it does not expose
the Hermes database or dashboard port directly.

This follows the current official OpenAI plugin MCP guidance:

- [Build an MCP server](https://developers.openai.com/plugins/build/mcp-server)
  specifies the official Python/TypeScript SDKs, streamable HTTP, tool
  annotations, authorization enforcement, and the stable `/mcp` endpoint.
- [Authenticate users](https://developers.openai.com/plugins/build/auth)
  specifies protected-resource metadata, OAuth 2.1 + PKCE, resource audience
  binding, and bearer-token verification.

## Deployment

The OCI machine already uses systemd services and OpenResty/1Panel for HTTPS.
The reproducible deployment artifacts are kept in this repository:

- `deploy/systemd/hermes-chatgpt-mcp.service` runs the independent service as
  the `ubuntu` user on loopback and restarts on failure.
- `deploy/openresty/kanban-mcp-locations.conf` contains the narrow proxy and
  metadata routes to include in the existing Kanban TLS virtual host.
- `scripts/install_oci.sh` validates paths, installs the unit/env directory,
  reloads systemd, validates OpenResty configuration, and performs health and
  unauthenticated/authenticated MCP probes without printing secrets.

The service is independently restartable from Hermes. Its only host data
dependency is read access to the canonical Hermes source and Kanban board
files.

## Chosen integration boundary

```text
ChatGPT web
    | HTTPS + OAuth 2.1 bearer token
    v
OpenResty: kanban.hermesinthenight.duckdns.org/mcp
    | loopback proxy, no direct database exposure
    v
hermes-chatgpt-mcp (FastMCP streamable HTTP)
    | read-only adapter; mode=ro + query_only
    v
Hermes hermes_cli.kanban_db pure query/model functions
    |
    v
Canonical Hermes SQLite Kanban state
```

The adapter never imports the mutating dashboard router, never invokes the
Hermes CLI, and never implements a parallel lifecycle/dispatcher.

## Gate A — architecture review

| Gate | Evidence/decision |
| --- | --- |
| Canonicality | Uses Hermes `Task`, `Run`, `Event`, board path resolution, and pure query functions. |
| Isolation | The integration receives `HERMES_AGENT_ROOT` and `HERMES_KANBAN_HOME`; it does not embed a physical path in domain logic and does not write Hermes data. |
| Read-only | SQLite URI `mode=ro`, `PRAGMA query_only=ON`, no `init_db`/writable `connect`, allowlisted read tools only, and a state-hash invariant test. |
| Stability | External schemas use task/board/graph/activity concepts and preserve raw Hermes status rather than exposing internal mutator methods. |
| Deployment | Independent loopback systemd service behind the existing HTTPS OpenResty edge. |
| Testability | Adapter unit/fixture tests, MCP contract tests through ASGI, OAuth tests, and a real live-board read-only smoke. |
| Result | PASS for the selected boundary; no Hermes change is required for v0.1. |

## Required Hermes changes

None. The existing pure query functions and dataclasses are sufficient when
given a connection opened by the integration in read-only mode. A future
generic Hermes `connect_read_only()` helper could reduce duplicated connection
setup, but adding it is not required to make this service safe and would
expand the v0.1 change surface.

## Rejected alternatives

1. **Call `hermes_cli.kanban_db.connect()`** — rejected because it performs
   writable schema/WAL initialization and migrations.
2. **Call the Hermes CLI as a subprocess** — rejected because CLI commands
   auto-initialize the database and command-level behavior is broader and less
   stable than the pure query layer.
3. **Use `HermesKanban` HTTP** — rejected because its process owns mutation
   routes and is not a read-only API.
4. **Expose the whole Hermes MCP/tool server** — rejected because it contains
   mutating Kanban tools and unrelated agent capabilities.
5. **Duplicate the scheduler/DAG rules** — rejected; the adapter only reads
   canonical links/statuses and presents bounded projections.
6. **Static API key as the ChatGPT production contract** — rejected as the
   primary design because current OpenAI guidance calls for OAuth 2.1 for
   authenticated remote MCP servers; static bearer support is limited to
   local/manual diagnostics if explicitly configured.

