# Independent final review

Review date: 2026-08-16 UTC

## Result

PASS. v0.3 preserves the v0.1 query-only boundary, adds canonical multi-board
discovery/routing, and keeps one separately authorized task-creation command.
No Hermes repository file was modified.

## Findings and resolutions

| Area | Finding | Resolution/evidence |
| --- | --- | --- |
| Canonicality | Hermes owns board discovery, paths, task creation, IDs, status derivation, parent links, events, and notification inheritance. | `HermesBoardResolver` uses canonical `list_boards`/`kanban_db_path`; `HermesCreateAdapter` calls only `hermes_cli.kanban_db.create_task` through `connect_closing`; no SQL write is present in the integration. |
| Multi-board resolution | An explicit slug must not silently fall back to the default. | Fixture and public A/B tests resolve `codex_app_server` and `dashboard` independently; unknown boards return `BOARD_NOT_FOUND`; omitted read policy fails safe to the default. |
| Board authorization | Hermes has no principal ACL to delegate to the MCP. | Service-level read/create allowlists are explicit, bounded, and documented; `list_boards` reports token-dependent create capability without claiming per-user ACL. |
| Query/command isolation | Reusing the v0.1 read adapter for writes would weaken `mode=ro` guarantees. | Separate `ReadOnlyHermesStore` and `HermesCreateAdapter`; all seven query tools use `mode=ro` plus `PRAGMA query_only=ON`. |
| Public mutation surface | A broad Hermes API or CLI would expose unrelated mutators. | MCP discovery returns exactly eight tools; `create_task` is the only write and no update/delete/claim/assign-after-create/move/start/complete/review/approve/reject/retry/import/sync tool is registered. |
| Scope isolation | A read token must remain usable for all v0.1 tools but unable to create. | Resource guard requires `hermes:read`; `create_task` performs an additional `hermes:create` check. Read-only token integration test is denied without a state change. |
| MCP annotations | Clients need an explicit distinction between query and additive write. | Seven tools: `readOnlyHint=true`; create: `readOnlyHint=false`, `destructiveHint=false`, `idempotentHint=true` because the MCP key is mandatory. |
| OAuth persistence | v0.1 in-memory DCR/refresh state would lose ChatGPT clients at restart. | DCR metadata and refresh-token hashes are atomically persisted at mode 0600 under systemd `StateDirectory`; access tokens remain signed/self-contained and auth codes remain ephemeral. Public post-restart client lookup and refresh rotation passed. |
| Validation | Unbounded or invented create fields could widen the command surface. | Strict schemas reject extras and bound title/body/parents/IDs/priority; only native create fields are exposed. Missing boards/parents fail closed. |
| Auditability | A ChatGPT card must look native to Hermes. | The command uses Hermes transaction/event/link semantics and canonical `created_by=chatgpt_mcp`; public `get_task`, `get_activity`, and `get_dispatch` verified the created task. |
| Retry safety | A remote timeout can cause ChatGPT to retry a write. | `idempotency_key` is mandatory; same-board repeat returns the canonical existing task and the public A/B smoke observed no duplicate. |
| Sandbox | Enabling writable command paths must not make the query path writable. | systemd keeps `ProtectSystem=full`, `ProtectHome=read-only`, `NoNewPrivileges`, board-specific `ReadWritePaths` for `codex_app_server`/`dashboard`, and a separate private OAuth state directory. |
| Edge/operations | Existing HTTPS/OpenResty infrastructure must remain the single edge. | The existing 1Panel OpenResty container passed syntax validation; service is loopback-only, enabled, active, and restartable. |

## Verification evidence

- Local suite: `52 passed`.
- Compile check: `compileall` passed.
- Real Hermes read smoke on `codex_app_server`: six canonical operations,
  fingerprint unchanged.
- Public v0.3 smoke: health, protected-resource and authorization-server
  metadata, eight-tool discovery, read/write annotations, explicit
  `codex_app_server`/`dashboard` reads, `hermes:read` create denial, real
  one-card-per-board `create_task`, idempotent retry, `get_task`,
  `get_activity`, `get_dispatch`, native cleanup, and post-restart client
  authorization lookup passed.
- `systemd-analyze verify`: exit code 0; service enabled and active with
  `ExecMainStatus=0` and no restart loop.
- OAuth state: version 1, mode 0600, private directory mode 0700; state file
  contains client metadata and refresh hashes only.
- OpenResty container: `/usr/local/openresty/bin/openresty -t` successful.
- TLS: `Verify return code: 0 (ok)`.
- Cleanup read check: zero `[mcp-v03-smoke ...]` rows on both controlled
  boards.
- Secret scan boundary: runtime env/state are outside Git; no credentials or
  bearer tokens are tracked.

## Known residual risks

- Board authorization is service-level, not per-principal/per-board: Hermes
  has no canonical principal ACL. The configured read/create allowlists are
  therefore the honest boundary; boards outside read access are collapsed to
  not-found.
- A single systemd instance is supported. Per-board create idempotency is
  serialized in-process; a multi-replica deployment would need shared
  coordination.
- Existing ChatGPT authorizations with only `hermes:read` need explicit OAuth
  reauthorization for `hermes:create`; persistent DCR clients survive restart.
- OAuth state is local to one systemd instance and intentionally has no
  distributed-store/cluster semantics.
- v0.3 is not full Kanban write management: `create_task` is the only write;
  comments, lifecycle, task editing, dispatch, and board administration remain
  deliberately unexposed.
- The deployment depends on the existing 1Panel/OpenResty reload hook and
  certificate renewal process; it does not own certificate issuance.
