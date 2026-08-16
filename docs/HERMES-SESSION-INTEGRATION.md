# Hermes session integration and source provenance

## Source identity

All capability claims in this document are pinned to the real Hermes Agent repository:

- Repository: https://github.com/NousResearch/hermes-agent
- Inspected source revision: `19b846543cff0da8a7e74cc4517b1ccb3f4d14f9`
- Reported version: Hermes Agent v0.20.1 (2026.8.13)
- Comparison point: `origin/main` was `86b2057a1b3365b93cedf1ea9b1962dfc6b08170` during the investigation.

The connector repository is not Hermes source. Its initial GitHub commit is only a LICENSE file;
no claims are derived from the connector repository's history.

## Primary source files and symbols

The investigation pinned the read paths to these Hermes symbols:

- `hermes_cli/sessions_cmd.py`: `cmd_sessions` list and export actions.
- `hermes_state.py`: `SessionDB.list_sessions_rich`, `get_session`, `resolve_session_id`,
  `get_messages`, `get_messages_around`, and `get_messages_as_conversation`.
- `hermes_state_portability.py`: `export_session` and `export_all`.
- `hermes_cli/web_routers/sessions.py`: `GET /api/sessions`, `GET /api/sessions/{id}`, and
  `GET /api/sessions/{id}/export`.
- `hermes_state_search.py` and `tools/session_search_tool.py`: FTS5-backed anchored session views.
- `agent/session_activity.py`: activity provenance and the 60-second minimum heartbeat constant.

The exact source revision above, rather than an abbreviated or connector-repository SHA, is the
provenance anchor for this document.

## Proven capabilities

The following are canonical read capabilities:

| Connector capability | Verified Hermes path |
|---|---|
| `list_sessions` | `hermes sessions list`, `SessionDB.list_sessions_rich`, or REST `GET /api/sessions` |
| `get_session` | `SessionDB.get_session` / `resolve_session_id`, or REST `GET /api/sessions/{id}` |
| `get_session_output` | `hermes sessions export`, portability exporters, or REST `GET /api/sessions/{id}/export` |

These paths are pull/read surfaces. The connector must preserve source/profile/session authorization
and must not claim a live event stream.

## Not proven as external capabilities

`send_session_input`, `create_session`, and `start_session`/`resume_session` are **not available
as safe external connector capabilities**. Internal Hermes paths exist (agent loop, gateway
incoming events, CLI interactivity, and local desktop RPC methods such as `prompt.submit`,
`session.create`, and `session.resume`), but they are not a general-purpose third-party API. The
CLI help was verified to contain no `create`, `start`, or input subcommand under `hermes sessions`.

The missing external write contract is intentional. Do not replace it with tmux, SSH, terminal,
filesystem, SQLite mutation, or process control. Multi-client safety and the browser-to-chat
submission protocol were not established.

## Cursor and output model

Hermes persists sessions and messages in profile `state.db`. `messages.id` is a monotonic integer
primary key in the observed schema, so an adapter can implement a session-scoped opaque cursor by
remembering the last message id and polling rows with a larger id. This is a feasibility finding,
not a guarantee of an external streaming API. `hermes sessions export` and its REST counterpart
are the canonical output representations; format and completeness must be declared by an adapter.

The legacy `~/.hermes/sessions/sessions.json` is a gateway-routing mirror, not the authoritative
session list. Session state includes lifecycle fields (`started_at`, `ended_at`, `end_reason`,
`archived`, `pinned`, `parent_session_id`) and activity fields (`last_activity_at`,
`last_activity_description`, `last_activity_provenance`). Persisted messages include role/content
and, where present, tool-call, reasoning, timestamp, and effect metadata.

## Event/state model

No external event feed was proven. Expose snapshots and cursor-based polling only. Do not invent
completion events, exactly-once delivery, or session state transitions from inactivity. Hermes'
activity heartbeat is observation metadata; it is not a delivery protocol.

## Authentication and boundaries

The web server defaults to loopback. Non-loopback exposure requires the inspected auth middleware
(OAuth/password or token-based controls); loopback operation is operator-trusted and must not be
advertised as public authorization. REST session reads use read-only database handles. CLI and
gateway surfaces are operator-owned and retain their routing/origin constraints.

Per-route OAuth scopes for session endpoints were not verified. A deployment must therefore define
and test least-privilege profile/session mapping before external access. Never disclose tokens,
conversation contents, or unnecessary routing identifiers in logs.

## Rejected shortcuts and non-goals

This integration is strictly ChatGPT ↔ Hermes Sessions. It excludes Kanban boards, tasks/DAGs,
TRIAGE/SPECIFY/DECOMPOSE, scheduling, planner/controller behavior, and arbitrary terminal, SSH,
filesystem, or process operations. Kanban MCP tool names and OAuth-like grant names are not Hermes
session evidence and cannot be converted into session capabilities by analogy.
