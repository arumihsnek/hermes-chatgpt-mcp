# Beta board-management operation record

Record date: 2026-08-17 UTC
Design/task date: 2026-08-16
Evidence type: checked-in implementation, contract tests, and deployment
artifacts.
Live deployment and ChatGPT validation: **PENDING**.

This record documents the behavior implemented on the beta branch. It does not
claim that the beta hostname, DNS, TLS certificate, OCI service, or an
interactive ChatGPT connection has been exercised.

## Endpoint and public-surface matrix

| Surface | Configured endpoint | Loopback | Tools | Supported scopes |
| --- | --- | --- | --- | --- |
| Stable | `https://kanban.hermesinthenight.duckdns.org/mcp` | `127.0.0.1:8789` | eight tools: `list_boards`, `get_board`, `list_tasks`, `get_task`, `get_task_graph`, `get_dispatch`, `get_activity`, `create_task` | `hermes:read`, `hermes:create`, `offline_access` |
| Beta | `https://kanban-beta.hermesinthenight.duckdns.org/mcp` | `127.0.0.1:8791` | eleven tools: the stable eight plus `create_board`, `add_comment`, `assign_task` | `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, `offline_access` |

The stable default registers no beta tools and does not advertise the beta
command scopes. Beta is selected explicitly through `MCP_SURFACE=beta` and the
beta entrypoint. The beta OpenResty include is for the beta hostname only; the
stable service, endpoint, environment, and OAuth state remain separate.

## Scope and board-grant behavior

- `hermes:read` authorizes the seven query tools and global active-board reads.
- `hermes:create` authorizes `create_task` only when the signed grant contains
  exactly one selected board and `board_access=write`.
- `hermes:manage` authorizes `add_comment` and `assign_task` only on that same
  one-board grant. It does not imply `hermes:create`.
- `hermes:board:create` authorizes the global `create_board` operation when
  `MCP_BOARD_CREATE_ENABLED=1`. It has no selected-board claim and is separate
  from the board-bound command scopes.
- `offline_access` is only the OAuth refresh protocol scope and grants no
  Hermes operation.

**create_board alone does not grant task-write access** to the board it
creates. A command-capable beta authorization must be completed separately,
selecting the new board for `hermes:create` or `hermes:manage`.

For `create_task`, `add_comment`, and `assign_task`, an omitted `board` uses
the signed grant board. An explicitly supplied board that differs from the
grant fails before command-adapter construction with
`BOARD_SESSION_MISMATCH`; it does not fall back to Hermes' current board.
Therefore, if the grant selected another board while Hermes reports
`seq66_looper` as its current default, an explicit request for `seq66_looper`
is an expected board-session mismatch. The mismatch identifies a grant/request
boundary, not a missing `seq66_looper` board.

`create_board` has no board-selection input. It calls Hermes' canonical board
creation function, returns safe board metadata, does not select the new board,
and does not change Hermes' current/default board. A later `list_boards` call
reports the unchanged `default_board` and the new named board separately.

## Canonical command mapping and exclusions

| Public operation | Adapter and canonical call | Observable canonical result |
| --- | --- | --- |
| `create_board` | `HermesBoardAdminAdapter` -> Hermes `create_board` | Safe board metadata; ordinary named creation is not the current default |
| `create_task` | Existing `HermesCreateAdapter` -> Hermes `create_task` | Canonical task, IDs, links, idempotency, and `created` event |
| `add_comment` | `HermesCardManagementAdapter` opens the selected board with `connect_closing`, calls `add_comment`, then reloads with `list_comments` | Comment identity, provenance `chatgpt_mcp`, and `commented` event |
| `assign_task` | `HermesCardManagementAdapter` opens the selected board with `connect_closing`, calls `assign_task`, then reloads with `get_task` | Assignee/status and `assigned` event |

The public beta surface has no tenant administration, board rename/archive/
delete, task update, lifecycle, controller, import, or sync operation. A task
`tenant` value remains task metadata and is not an ACL. This repository adds no
task or board mutation SQL.

## Query, command, and persistence boundaries

The seven reads use the existing query adapter with SQLite URI `mode=ro` and
immediate `PRAGMA query_only=ON`. The four public beta/stable commands use
separate canonical Hermes command adapters and connections. Read authorization
does not reach a command adapter, and command failures are returned as bounded
public codes rather than paths or stack traces.

Stable persists its DCR metadata, refresh-grant records, and revoked-grant
identifiers under `/var/lib/hermes-chatgpt-mcp/oauth-state.json`. Beta persists
the corresponding state under
`/var/lib/hermes-chatgpt-mcp-beta/oauth-state.json`; it does not read stable
state. The beta environment is
`/home/ubuntu/.hermes/hermes-chatgpt-mcp-beta.env`, with a signing key separate
from stable and mode `0600`. Authorization codes remain in memory and are not
restored after restart. No credential values, token values, or authorization
codes are part of this record.

## Deployment, health, restart, and rollback

The prepared beta installer is invoked with an exact candidate commit:

```bash
./scripts/install_oci_beta.sh <exact-beta-commit>
```

It requires the candidate worktree to be clean and at the requested commit,
validates the beta edge include before mutation, installs only the beta unit
and include, creates the beta state directory, writes/preserves the private
environment without printing it, runs an OpenResty syntax check, restarts only
`hermes-chatgpt-mcp-beta.service`, and checks
`GET http://127.0.0.1:8791/healthz` for `{"status":"ok"}` before reloading the
OpenResty hook. Its systemd unit uses `Restart=on-failure`, a five-second
restart delay, restrictive filesystem/process settings, and write access to
canonical named-board storage plus its own state directory.

If a beta installation fails after mutation begins, the installer exit trap
restores the prior beta unit, include, edge configuration, environment, and
service state. When an edge reload was attempted, it validates and reloads the
restored edge. The rollback path does not restart or rewrite the stable unit.
For a deliberate user-facing fallback, keep stable intact and reconnect to
the stable endpoint; stable OAuth authorization is independent of beta OAuth.

All live installer, DNS/TLS, OCI, health, OAuth, and ChatGPT checks are
**PENDING**. No deployment or service restart is evidence in this record.

## Bounded dogfood prompt

```text
Use the beta MCP connection for a bounded board-management dogfood.

1. Call list_boards and record default_board and the visible capability flags.
2. Choose a uniquely named valid test-board slug using the current UTC time.
3. Call create_board once with that slug and a test-only name.
4. Call list_boards again and verify exactly one item has the new slug and the
   current default_board is unchanged.
5. Stop and tell the user to authorize/reconnect the beta connector and select
   the new board for a one-board command grant. Explain that create_board alone
   does not grant task-write access. Do not continue before authorization.
6. After authorization, create exactly one test card with create_task and a
   unique idempotency key.
7. Add one comment with add_comment.
8. assign it once with assign_task, then report only returned public identities.
```

The prompt is bounded to one created board, one card, one comment, and one
assignment. It is a future controlled procedure, not a report of live success.
