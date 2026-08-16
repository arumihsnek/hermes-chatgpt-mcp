# Security boundaries

## Security posture

The intended connector is read-only and session-scoped. This repository contains no connector
implementation, credentials, OAuth configuration, or deployment instructions. The design must
not turn a read integration into arbitrary control of the Hermes host.

## Trust and authorization

Hermes' web server defaults to loopback (`127.0.0.1:9119`). The inspected source requires
OAuth/password or token-based authentication when the server is exposed beyond loopback; loopback
trust is not a reason to expose the service publicly. Session REST reads open the profile database
read-only. A deployment must still enforce a caller-to-profile/session mapping before returning
any data.

The local CLI and messaging gateway are operator-owned surfaces. Their routing/session keys and
origin fields are part of Hermes' boundary; an MCP adapter must not bypass them or resolve an
arbitrary session supplied by an untrusted caller. Per-route OAuth scopes for the session REST
endpoints were not established by the source investigation and must be verified before deployment.

## Data handling

- Treat session metadata, messages, tool calls, reasoning, and exports as sensitive.
- Return only fields required by the requested operation.
- Do not log tokens, authorization headers, full exports, or raw conversation content by default.
- Keep cursors opaque and session-bound; do not use them as authorization credentials.
- Use read-only database handles where direct state access is unavoidable.
- Respect Hermes profile and filesystem permissions; do not weaken them.

## Forbidden shortcuts

The connector must never implement missing write operations with tmux, SSH, terminal commands,
filesystem edits, SQLite writes, process signals, or other host-control mechanisms. It must not map
Kanban operations or grants (`list_tasks`, `get_task`, `create_task`, or invented `hermes:read` /
`hermes:create` scopes) into session capabilities.

## Known evidence gaps

The investigation did not establish multi-client safety for local desktop RPC methods, the exact
browser-to-REST chat submission protocol, or per-route OAuth scope definitions. These are blockers
for any write or public-network extension, not assumptions to fill in by analogy.

## Reporting

Security issues should include the affected interface, Hermes source revision, profile boundary,
and a minimal reproduction without sharing session contents or secrets. Do not report credentials
or copied exports in issues.
