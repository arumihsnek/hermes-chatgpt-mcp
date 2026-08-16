# Independent final review

Review date: 2026-08-16 UTC

## Result

PASS. v0.2 preserves the v0.1 query-only boundary and adds one separately
authorized, canonical Hermes task-creation command. No Hermes repository file
was modified.

## Findings and resolutions

| Area | Finding | Resolution/evidence |
| --- | --- | --- |
| Canonicality | Hermes owns task creation, IDs, status derivation, parent links, events, and notification inheritance. | `HermesCreateAdapter` calls only `hermes_cli.kanban_db.create_task` through `connect_closing`; no SQL write is present in the integration. |
| Query/command isolation | Reusing the v0.1 read adapter for writes would weaken `mode=ro` guarantees. | Separate `ReadOnlyHermesStore` and `HermesCreateAdapter`; the six query tools still use `mode=ro` plus `PRAGMA query_only=ON`. |
| Public mutation surface | A broad Hermes API or CLI would expose unrelated mutators. | MCP discovery returns exactly seven tools; `create_task` is the only write and no update/delete/claim/assign-after-create/move/start/complete/review/approve/reject/retry/import/sync tool is registered. |
| Scope isolation | A read token must remain usable for all v0.1 tools but unable to create. | Resource guard requires `hermes:read`; `create_task` performs an additional `hermes:create` check. Read-only token integration test is denied without a state change. |
| MCP annotations | Clients need an explicit distinction between query and additive write. | Six tools: `readOnlyHint=true`; create: `readOnlyHint=false`, `destructiveHint=false`, `idempotentHint=false`. The annotations match the current SDK/spec vocabulary. |
| OAuth persistence | v0.1 in-memory DCR/refresh state would lose ChatGPT clients at restart. | DCR metadata and refresh-token hashes are atomically persisted at mode 0600 under systemd `StateDirectory`; access tokens remain signed/self-contained and auth codes remain ephemeral. Public post-restart client lookup and refresh rotation passed. |
| Validation | Unbounded or invented create fields could widen the command surface. | Strict schemas reject extras and bound title/body/parents/IDs/priority; only native create fields are exposed. Missing boards/parents fail closed. |
| Auditability | A ChatGPT card must look native to Hermes. | The command uses Hermes transaction/event/link semantics and canonical `created_by=chatgpt_mcp`; public `get_task`, `get_activity`, and `get_dispatch` verified the created task. |
| Sandbox | Enabling a writable command path must not make the query path writable. | systemd keeps `ProtectSystem=full`, `ProtectHome=read-only`, `NoNewPrivileges`, board-specific `ReadWritePaths`, and a separate private OAuth state directory. |
| Edge/operations | Existing HTTPS/OpenResty infrastructure must remain the single edge. | The existing 1Panel OpenResty container passed syntax validation; service is loopback-only, enabled, active, and restartable. |

## Verification evidence

- Local suite: `36 passed`.
- Compile check: `compileall` passed.
- Real Hermes read smoke on `codex_app_server`: six canonical operations,
  fingerprint unchanged.
- Public v0.2 smoke: health, protected-resource and authorization-server
  metadata, DCR, PKCE, seven-tool discovery, annotations, real `create_task`,
  `get_task`, `get_activity`, `get_dispatch`, restart, refresh-token rotation,
  and cleanup passed.
- `systemd-analyze verify`: exit code 0; service enabled and active with
  `ExecMainStatus=0` and no restart loop.
- OAuth state: version 1, mode 0600, private directory mode 0700; state file
  contains client metadata and refresh hashes only.
- OpenResty container: `/usr/local/openresty/bin/openresty -t` successful.
- TLS: `Verify return code: 0 (ok)`.
- Cleanup read check: `v02_validation_rows=0`.
- Secret scan boundary: runtime env/state are outside Git; no credentials or
  bearer tokens are tracked.

## Known residual risks

- One configured board is served per process; changing the board requires a
  service restart and the board-specific systemd write path must change with
  it.
- Existing v0.1 DCR clients lived only in the old process memory. The first
  restart after this rollout can require ChatGPT reauthorization; clients
  registered after persistent state is active survive later restarts.
- OAuth state is local to one systemd instance and intentionally has no
  distributed-store/cluster semantics.
- v0.2 is not full Kanban write management: `create_task` is the only write.
- The deployment depends on the existing 1Panel/OpenResty reload hook and
  certificate renewal process; it does not own certificate issuance.
