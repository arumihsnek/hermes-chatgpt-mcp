# Session-only connector specification

## 1. Contract status

This is a proposed read-only MCP contract, not an implementation. It is limited to the ChatGPT
↔ Hermes Agent session domain. A connector MUST fail closed when the configured Hermes source,
profile, or authorization boundary cannot be established.

## 2. Operations

### `list_sessions`

Returns session summaries from a canonical Hermes read path. The implementation may use
`hermes sessions list` or `GET /api/sessions` when the Hermes web server is running. A summary may
include the Hermes session id, display/title fields, source/routing metadata permitted to the
caller, timestamps, lifecycle state, activity snapshot, and message counts. The connector must
not expose unrelated profiles or sessions outside the caller's authorized origin.

### `get_session`

Accepts a Hermes session id (or a documented canonical resolver form) and returns metadata for
that session. It must preserve Hermes' session identity and must not treat an MCP request/session
identifier as a Hermes session id.

### `get_session_output`

Accepts a Hermes session id and an optional output format/cursor. The canonical sources are
`hermes sessions export` or `GET /api/sessions/{id}/export`; the exact export format must be
preserved or explicitly declared. Direct state-store reads are an implementation option only
when they use the same read-only session model and authorization checks.

## 3. Cursor and output model

Hermes stores messages with an integer primary key. A read adapter may use a cursor containing the
last observed message id and query the same session for rows with a greater id. Cursors are opaque
to ChatGPT, scoped to one Hermes session and one output representation, and must be rejected when
used with another session or incompatible source snapshot. Export output is pull-based; no live
streaming or delivery guarantee is implied.

The observed session store is SQLite (`state.db`) with `sessions`, `messages`, FTS5 message indexes,
and turn-lease state. The legacy `sessions.json` file is a routing mirror, not the authoritative
session list.

## 4. State and events

Session lifecycle is represented by fields such as `started_at`, `ended_at`, `end_reason`,
`archived`, `pinned`, and `parent_session_id`. Activity is represented by
`last_activity_at`, `last_activity_description`, and `last_activity_provenance`; the inspected
source defines a 60-second minimum heartbeat interval. Message rows carry role, content, tool-call,
reasoning, timestamp, and effect metadata where present.

These are observed persistence fields, not a promise that Hermes emits an external event stream.
The connector therefore exposes snapshots/exports and cursor-based polling only. It must not
invent session events, infer completion from inactivity, or claim exactly-once delivery.

## 5. Explicitly unavailable operations

The following are not connector capabilities in this specification:

- `send_session_input`
- `create_session`
- `start_session` / `resume_session`

Hermes has internal agent-loop, gateway, CLI, and local desktop RPC paths related to these actions,
but the verified source provides no safe general-purpose external API for them. In particular,
`hermes sessions` has no create/start/input subcommand and the inspected REST session surface has
no prompt-submit route. A future write API needs its own product and security decision.

## 6. Non-goals

No Kanban boards, tasks, DAGs, TRIAGE/SPECIFY/DECOMPOSE workflows, scheduling, planner/controller
operations, OAuth scope invention, arbitrary terminal/SSH/filesystem/process control, or host
administration belong in this connector.

## 7. Compatibility and failure behavior

The adapter must report unsupported, unauthorized, missing, or ambiguous operations rather than
falling back to an analogous interface. It must identify the Hermes source revision and selected
profile in diagnostics without disclosing secrets or full conversation contents.
