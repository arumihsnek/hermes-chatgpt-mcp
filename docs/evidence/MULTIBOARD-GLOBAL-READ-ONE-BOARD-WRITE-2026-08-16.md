# Multi-board global read and single-board write evidence

Date: 2026-08-16 UTC  
Code: `17a1cff` (`fix: migrate legacy unbound OAuth grants safely`)

## Observed facts

- The canonical Hermes installation is `/home/ubuntu/hermes-agent`; no Hermes
  source file was modified.
- Hermes reported 12 active canonical boards:
  `default`, `codex_app_server`, `dashboard`, `hermes-android`,
  `hermes-dojo-cross-profile`, `hermes-tasker`, `kanban-autonomy-hardening`,
  `miniapp`, `profile-factory`, `seq66_looper`, `tasker-safe-update-v1`, and
  `wilson-proposals`.
- Hermes' current default at verification time was `seq66_looper`.
- The deployed service was `active`, `enabled`, `ExecMainStatus=0`, and
  `NRestarts=0`; `systemd-analyze verify` returned successfully.
- TLS `/healthz`, authorization-server metadata, and protected-resource
  metadata returned HTTP 200. The advertised scopes were
  `hermes:read hermes:create offline_access`, and revocation metadata was
  present.
- Authenticated MCP discovery returned exactly eight tools: seven read tools
  and `create_task`.
- An authenticated read probe returned all 12 board slugs. Every board
  advertised `read=true`; the read-only probe advertised no create capability.
- Explicit live reads returned `codex_app_server` and `hermes-tasker` without
  crossing board boundaries. The live two-board read smoke passed without
  requesting writes.
- A read-only token calling `create_task` was rejected with
  `SCOPE_REQUIRED`; no command adapter was reached.

## OAuth-state migration

Before the deployment, the private state file was version 1 with five clients
and nine refresh records. The safe metadata summary showed three records with
`hermes:create` but no board grant and two records whose scopes exceeded the
registered client metadata. No token or raw state value was printed.

The root cause was historical v0.2 state: refresh grants could contain the
create scope without the v0.4 board claim. The v0.4 loader initially treated
that historical relationship as fatal and prevented service startup.

The migration now:

1. accepts the legacy state version;
2. preserves valid read refresh records;
3. preserves only write records with a valid board and `board_access=write`;
4. drops unbound historical write records without manufacturing a board; and
5. atomically rewrites the state as version 2.

After restart, the state was version 2 with five clients, six read refresh
records, zero unbound create refresh records, mode `0600`, and a mode `0700`
parent directory.

## Authorization semantics verified in tests

- Read consent strips `hermes:create` and produces a global-read token with no
  board write claim.
- Write consent requires `hermes:create` and one selected board.
- Access-token and refresh-token claims preserve that board.
- A write token selecting board A cannot create on board B.
- Revocation invalidates the complete grant.
- Existing unbound legacy write refresh records are discarded during migration.

## Not yet observed

This evidence does not claim that a fresh interactive ChatGPT authorization has
been completed after this deployment. Existing clients whose DCR metadata or
grant is read-only must be re-registered/reauthorized so ChatGPT requests
`hermes:create`; the consent page then selects one board. No live write card
was created during this verification run.
