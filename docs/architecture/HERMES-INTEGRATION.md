# Hermes integration reconnaissance

Status: architecture selected for MCP v0.4 (2026-08-16)

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

The Hermes companion WebUI is a separate service. It imports
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

Boards are implemented and discovered canonically in `hermes_cli.kanban_db`:

- The default board uses `<Hermes root>/kanban.db` for backwards compatibility.
- Named boards use `<Hermes root>/kanban/boards/<slug>/kanban.db`.
- Board metadata is read from `board.json` under the board directory.
- `list_boards(include_archived=False)` is the source used for discovery;
  `kanban_db_path(board=<slug>)` is the source used for exact path resolution.
- The active/default board is selected by Hermes' existing resolution chain,
  including `HERMES_KANBAN_BOARD` and `<Hermes root>/kanban/current`.
- Slugs are validated by Hermes' lowercase alphanumeric/hyphen/underscore
  contract.

The MCP service adds no registry. It discovers the canonical active list and
applies an optional bounded deployment policy on top of it:

```text
MCP_KANBAN_READ_BOARDS   = <optional operational cap>
MCP_KANBAN_CREATE_BOARDS = <optional operational cap>
```

When both variables are omitted, every active *named* canonical board is
readable and eligible for a write grant. Hermes also returns the root SQLite
database as a legacy `default` alias, but that alias is not a user-addressable
board: it has no board metadata and its WAL/SHM sidecars are shared with other
Hermes processes. The MCP resolver deliberately filters that alias and returns
`BOARD_NOT_FOUND` if it is requested. This is a boundary around Hermes'
canonical named-board model, not a parallel registry.

Explicit values remain service-level caps, not Hermes ACLs. Hermes has no
canonical principal-to-board authorization model in the inspected checkout,
so `hermes:read` is intentionally global to the resource owner and the
per-board write boundary is carried by the OAuth grant. A board outside an
explicit read cap is deliberately reported as unavailable rather than
revealing whether it exists.

The service never enumerates arbitrary filesystem directories and never
exposes `db_path`, `default_workdir`, or other path-bearing metadata. The
current OCI installation follows Hermes' current default dynamically; a
static `HERMES_KANBAN_BOARD` remains available only as an explicit deployment
override.

## Board discovery and resolution (v0.4)

The resolver is `hermes_chatgpt_mcp.boards.HermesBoardResolver`. It loads the
Hermes module, verifies that the configured Kanban home is Hermes'
`kanban_home()`, rejects ambient `HERMES_KANBAN_DB`, and resolves every slug
through Hermes' `list_boards()` plus `kanban_db_path(board=...)`.

```text
ChatGPT
   | OAuth principal/scopes
   v
MCP
   | canonical resolver + optional deployment caps
   v
active named Hermes board
   ├── READ   -> ReadOnlyHermesStore (mode=ro, query_only=ON)
   └── WRITE  -> one-board OAuth grant -> HermesCreateAdapter
                                      -> canonical create_task
```

The semantics are explicit:

- omitted `board` resolves to the configured `HERMES_KANBAN_BOARD`; if absent,
  the resolver follows Hermes' current-board API dynamically;
- supplied `board` resolves exactly to that canonical slug;
- an unknown, unreadable, or non-read-authorized slug never falls back to the
  default;
- read discovery includes all active canonical boards unless an explicit
  deployment cap is configured;
- `create_task` requires `hermes:create` plus signed `board=<slug>` and
  `board_access=write` claims. A request for another board returns
  `BOARD_SESSION_MISMATCH` and never falls back;
- discovery is bounded by `MCP_MAX_BOARD_COUNT` and returns only safe metadata,
  canonical status counts, and `read`/`create` capabilities.

The authorization page offers two resource-owner choices: read-only access to
all boards, or read plus write access to exactly one selected board. The
selected board is not a mutable MCP session variable; it is part of the OAuth
grant and is preserved across refresh-token rotation until `/oauth/revoke`.
This makes changing the write board an explicit reauthorization rather than a
tool call that could self-grant permission.

## Beta board-management boundary

The beta entrypoint selects an explicit authorization policy and registers the
stable seven reads plus `create_task`, `create_board`, `add_comment`, and
`assign_task`—eleven tools total. The stable entrypoint remains eight tools and
does not register the beta tools or advertise `hermes:manage` or
`hermes:board:create`.

The exact beta command mapping is:

| MCP tool | OAuth requirement | Hermes canonical boundary | Resulting state |
| --- | --- | --- | --- |
| `create_board` | Global `hermes:board:create`; board creation flag enabled | `HermesBoardAdminAdapter.create_board` -> `hermes_cli.kanban_db.create_board` | Canonical board metadata; no board selection and no task-write grant |
| `create_task` | `hermes:create` plus one-board `board_access=write` grant | Existing `HermesCreateAdapter` -> `hermes_cli.kanban_db.create_task` | Canonical task and `created` event |
| `add_comment` | `hermes:manage` plus the exact selected board | `HermesCardManagementAdapter.add_comment` -> `connect_closing(..., board=...)`, `add_comment`, `list_comments` | Canonical comment and `commented` event; provenance `chatgpt_mcp` |
| `assign_task` | `hermes:manage` plus the exact selected board | `HermesCardManagementAdapter.assign_task` -> `connect_closing(..., board=...)`, `assign_task`, `get_task` | Canonical assignee and `assigned` event |

The beta board-creation grant is global and has no board claim. It cannot be
combined with the board-bound command scopes. Consequently, **create_board
alone does not grant task-write access** to the new board. A later OAuth
authorization must select that board for `hermes:create` or `hermes:manage`.
No tenant administration, board rename/archive/delete, task update, or
lifecycle/controller/import/sync operation is public. A task `tenant` value
remains canonical task metadata and is not authorization.

Creating a named board does not call Hermes' current-board setter and does not
change `default_board`. `list_boards` exposes the unchanged current default,
the new board's `is_default` value, and the beta capabilities. If a command
grant selected another board while Hermes' current default is
`seq66_looper`, an explicit command request for `seq66_looper` correctly
returns `BOARD_SESSION_MISMATCH`; an omitted command board routes to the
signed grant board instead of falling back to the current default.

## Board, tenant, and session semantics

These identifiers are deliberately not conflated:

| Field | Hermes meaning | Authorization meaning |
| --- | --- | --- |
| `board` | Selects the canonical Kanban database and board metadata namespace. | Read is global by default; write is bound to the one OAuth-selected board. |
| `tenant` | Optional task column used by Hermes for task grouping/filtering. | Not an ACL and not a substitute for board authorization. |
| `session_id` | Optional originating Hermes agent/chat session identifier stored on the task. | Not an OAuth principal and not an ACL. |
| `project_id` | Canonical project/workspace routing metadata inherited by Hermes where applicable. | Not exposed as an authorization control. |

The MCP `tenant` and `session_id` fields preserve their native task metadata
semantics; they cannot select another board or widen permissions.

## Canonical management reconnaissance

Hermes has canonical functions for substantially more operations, but their
existence is not sufficient reason to expose them. The decision matrix is:

| Operation family | Canonical Hermes API | Invariants centralized | MCP v0.4 decision | Risk |
| --- | --- | --- | --- | --- |
| `create_task` | `kanban_db.create_task` | Yes: IDs, parents, status, events, notification inheritance, idempotency | Expose on stable and beta | Medium |
| `add_comment` | `kanban_db.add_comment` | Yes: comment row/event semantics | Expose only on beta under `hermes:manage` and one-board binding | Low/medium |
| attachments/evidence | `kanban_db.add_attachment` and attachment helpers | Yes, but includes local file/path handling | Do not expose | Medium |
| title/body/priority/model/triage edits | canonical setters/specification functions | Yes | Do not expose | Medium/high |
| assign/reassign/link/unlink/block/promote/archive/delete | canonical commands exist | Yes | Expose only beta `assign_task`; keep all other operations private | High |
| claim/complete/review/reopen/retry/dispatch | controller/worker protocol functions exist | Yes, with ownership and evidence side effects | Do not expose | Very high |
| board create/rename/archive/delete | canonical board administration exists | Yes, but administrative | Expose only beta `create_board` with `hermes:board:create`; keep rename/archive/delete private | Critical |

In particular, the MCP does not turn any of these functions into a generic
`update_task` dictionary or emulate lifecycle transitions by changing columns.

## Error and retry model

The resolver and command boundary use stable public codes where the current
MCP framework permits tool errors: `BOARD_NOT_FOUND`,
`BOARD_NOT_ALLOWED`, `BOARD_SESSION_MISMATCH`, `BOARD_WRITE_SELECTION_REQUIRED`,
`TASK_NOT_FOUND`, `SCOPE_REQUIRED`, `CONFLICT`, and
`BACKEND_ERROR`. Schema failures are rejected by the strict MCP/Pydantic input
model before the tool body runs. Board authorization intentionally collapses
unknown and unread-authorized boards into `BOARD_NOT_FOUND` to avoid an
existence leak. A board outside an explicit deployment create cap is
`BOARD_NOT_ALLOWED`; a board different from the OAuth-selected write board is
`BOARD_SESSION_MISMATCH`.

`create_task` requires an `idempotency_key` bounded to the MCP schema. Hermes'
canonical lookup is scoped to the selected board database, so the same key is
independent on board A and board B. A retry with the same key returns the
canonical existing task; a different key is a new creation. The service also
serializes create calls per board within one process. A multi-replica
deployment would require an external coordination/idempotency layer and is
not supported by this single-process deployment.

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

## Canonical command path — create_task (v0.4)

Hermes has a canonical create operation in
`hermes_cli.kanban_db.create_task`. The native CLI command
`hermes kanban create` is a thin parser layer over that function; it does not
define a second task model. The integration therefore calls the canonical
function directly from a separate command adapter rather than shelling out to
the CLI or issuing SQL of its own.

The command adapter opens a normal Hermes command connection with
`kanban_db.connect_closing(board=<configured board>)`. This is deliberately
not the `ReadOnlyHermesStore` and is the only code path in this repository
allowed to obtain a writable Hermes connection. The command adapter exposes
one method, `create_task`, and does not import or dispatch any other Hermes
mutator.

The canonical operation supplies the following semantics that the MCP layer
preserves:

- IDs are generated by Hermes as `t_<random hex>`;
- title is required and assignees are normalized by Hermes;
- `parents` are validated in the same transaction, inserted into
  `task_links`, and determine `ready` versus `todo`;
- `triage=True` produces `triage`; the command adapter fixes
  `initial_status="running"` and does not expose arbitrary initial states;
- `priority`, `tenant`, `session_id`, `body`, and `idempotency_key` retain
  their native meanings;
- the canonical `created` task event is appended and notification
  subscriptions are inherited through Hermes' existing helper;
- duplicate non-archived `idempotency_key` values return the existing task ID
  according to Hermes' native behavior. The MCP schema makes this key
  mandatory because a remote timeout can otherwise be retried as a duplicate
  card. The adapter serializes creation per board in-process; Hermes remains
  responsible for the transaction and canonical audit event.

The public MCP schema intentionally exposes only the safe subset needed for a
new card: configured `board`, `title`, `body`, `parent_ids`, `assignee`,
`priority`, `tenant`, `session_id`, `triage`, and `idempotency_key`. It does
not expose workspace paths, project routing, model/provider overrides,
skills, retry policy, or any post-creation mutation. `acceptance_criteria` is
not a Hermes task field; callers should put that content in the canonical
`body` field. The adapter supplies the canonical `created_by` value
`chatgpt_mcp` as provenance metadata; it does not create a parallel audit
system.

Validation is layered: strict Pydantic input models bound size, count, ID,
priority, and enum values before the command path; the resolver validates the
exact board and operation policy; Hermes then performs its own normalization,
parent existence checks, transaction, and invariants. Errors are returned as
sanitized MCP tool errors and never expose SQL, filesystem paths, or stack
traces.

## Query/command separation Gate A (v0.4)

The selected boundary is:

```text
ChatGPT
  | hermes:read                         | hermes:read + hermes:create
  | all active boards                   | board=<one slug>, access=write
  v                                     v
MCP read tools                       MCP create_task
  |                                     |
ReadOnlyHermesStore                  HermesCreateAdapter
  | mode=ro + query_only              | kanban_db.connect_closing()
  v                                     v
Hermes pure queries                  Hermes kanban_db.create_task()
  \____________________________________/
                canonical Hermes state
```

The two paths do not share a connection or adapter. A read token cannot call
`create_task`; the MCP handler checks `hermes:create` in addition to the
resource-wide `hermes:read` requirement. The seven query tools retain their
read-only annotations and scope. The create tool is the only public mutator
and is annotated `readOnlyHint=false`, `destructiveHint=false` (additive
write), and `idempotentHint=true`; its required idempotency key maps retries
to Hermes' existing non-archived task. A create request cannot select a board
other than the board claim in its OAuth grant.

The service sandbox grants write access only to the canonical boards storage
and the service-owned OAuth state directory. The query adapter continues to
use SQLite `mode=ro` and `PRAGMA query_only=ON`; enabling the separate command
connection does not weaken that invariant.

The beta extension preserves this Gate A boundary:

```text
ChatGPT
  | hermes:read                         | beta command scope + one board
  | all active boards                   | board=<one slug>, access=write
  v                                     v
MCP read tools                       beta command tools
  |                                     |
ReadOnlyHermesStore                  narrow canonical adapters
  | mode=ro + query_only              | Hermes command connection
  v                                     v
Hermes pure queries                  canonical board/task state
```

`create_board` is the exception to the board-bound command grant: it requires
global `hermes:board:create`, has no board input, and never changes Hermes'
current/default board. The beta query path remains read-only and the command
path remains the only writable path. Stable continues to expose only its
original `create_task` command.

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
contains Hermes' legacy root database at `/home/ubuntu/.hermes/kanban.db` and
named board databases under `/home/ubuntu/.hermes/kanban/boards/`. The legacy
root database remains owned by Hermes and is intentionally outside this MCP
service's board surface; only the named board directory is granted to the
systemd sandbox.

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
- required resource scope `hermes:read` and an audience/resource check;
- separate `hermes:create` scope, checked only by `create_task`. A creation
  grant requests both scopes because the MCP resource is globally protected by
  `hermes:read`; a read-only grant remains unable to create.
- `offline_access` is advertised only as the OAuth refresh-token protocol
  scope; it does not authorize any Hermes operation.

On beta, `hermes:manage` authorizes only the append-only comment and assignment
commands on the one selected board; it does not imply `hermes:create`.
`hermes:board:create` is global and cannot carry a board claim. The beta DCR
and refresh state is persisted under `/var/lib/hermes-chatgpt-mcp-beta/`,
separate from stable; authorization codes remain ephemeral. A fresh ChatGPT
connection or reauthorization is required to select a beta write board.

DCR client registrations and refresh-token rotation state are persisted in a
0600 service-owned state file under `/var/lib/hermes-chatgpt-mcp/`. Access
tokens are signed and self-contained; authorization codes remain short-lived
and in memory as ephemeral state. Secrets (OAuth password, signing key, and
refresh-token hashes) are never committed. The state directory is created by
systemd with restrictive permissions and is independent of the Hermes
database.

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
  the `ubuntu` user on loopback, creates a private state directory, and
  restarts on failure.
- `deploy/openresty/kanban-mcp-locations.conf` contains the narrow proxy and
  metadata routes to include in the existing Kanban TLS virtual host.
- `scripts/install_oci.sh` validates paths, installs the unit/env directory,
  reloads systemd, validates OpenResty configuration, and performs health and
  unauthenticated/authenticated MCP probes without printing secrets.

The service is independently restartable from Hermes. Its host dependencies
are the canonical Hermes source, the active named-board storage, and its own
OAuth state directory. Optional board caps can narrow this set, but the OCI
default exposes all active named boards for read discovery. The command path
does not expose the Hermes HTTP API or grant general filesystem/database
access.

The beta artifacts add `hermes-chatgpt-mcp-beta.service`, a separate
`127.0.0.1:8791` listener, and an OpenResty include for
`kanban-beta.hermesinthenight.duckdns.org`. The installer validates the
candidate commit and edge syntax before mutation, checks beta `/healthz` after
restart, and has a beta-only rollback path. Public DNS/TLS, OCI installation,
and ChatGPT connection validation remain pending until an operator performs
those checks.

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
| Isolation | The integration receives `HERMES_AGENT_ROOT` and `HERMES_KANBAN_HOME`; it resolves canonical board paths and grants only the command sandbox write boundary. |
| Read-only | SQLite URI `mode=ro`, `PRAGMA query_only=ON`, no `init_db`/writable `connect` from the query adapter, seven explicitly registered read tools, and a state-hash invariant test. |
| Command safety | Only `HermesCreateAdapter.create_task` can obtain the canonical writable connection; no SQL write is present in the MCP repository. |
| Scope isolation | Resource authentication requires `hermes:read`; `create_task` additionally requires `hermes:create`; read-only tokens are denied. |
| Persistence | DCR clients and refresh-token hashes survive service restart in a mode-600 service state file; authorization codes remain ephemeral. |
| Stability | External schemas use board/task/graph/activity concepts and preserve raw Hermes status rather than exposing internal mutator methods. |
| Deployment | Independent loopback systemd service behind the existing HTTPS OpenResty edge. |
| Testability | Adapter unit/fixture tests, MCP contract tests through ASGI, OAuth tests, and a real live-board read-only smoke. |
| Result | PASS for the selected v0.4 boundary; no Hermes change is required. |

## Required Hermes changes

None. Hermes already exposes the canonical `kanban_db.create_task` operation
and its transaction/audit semantics. The integration only supplies a narrow
adapter and does not add ChatGPT-specific code to Hermes.

## Rejected alternatives

1. **Put writes through `ReadOnlyHermesStore`** — rejected because it would
   collapse the query/command boundary and weaken the v0.1 fingerprint proof.
2. **Issue `INSERT INTO tasks` from this repository** — rejected because it
   would duplicate Hermes validation, ID generation, links, event, and
   notification semantics.
3. **Call `hermes_cli.kanban_db.connect()` for queries** — rejected because it
   performs writable schema/WAL initialization and migrations.
4. **Call the Hermes CLI as a subprocess** — rejected because the CLI adds
   parser/process coupling and the canonical Python command operation is
   directly available.
5. **Use `HermesKanban` HTTP** — rejected because its process owns broad
   mutation routes and is not a one-operation command boundary.
6. **Expose the whole Hermes MCP/tool server** — rejected because it contains
   mutating Kanban tools and unrelated agent capabilities.
7. **Duplicate the scheduler/DAG rules** — rejected; the adapter only reads
   canonical links/statuses and presents bounded projections.
8. **Static API key as the ChatGPT production contract** — rejected as the
   primary design because current OpenAI guidance calls for OAuth 2.1 for
   authenticated remote MCP servers; static bearer support is limited to
   local/manual diagnostics if explicitly configured.
