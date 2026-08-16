# Independent final review

Review date: 2026-08-16 UTC

## Result

PASS for the v0.4 code boundary. The service preserves the v0.1 query-only
path, discovers all active canonical Hermes boards by default, and binds the
only write operation to one OAuth-selected board. No Hermes repository file
was modified.

## Findings and resolutions

| Area | Finding | Resolution/evidence |
| --- | --- | --- |
| Canonicality | Hermes owns board discovery, paths, task creation, IDs, status derivation, parent links, events, and notification inheritance. | `HermesBoardResolver` uses canonical `list_boards`/`kanban_db_path`; `HermesCreateAdapter` calls only `hermes_cli.kanban_db.create_task` through `connect_closing`; no SQL write is present in the integration. |
| Multi-board resolution | An explicit slug must not silently fall back to the default. | Fixture A/B tests resolve independently; unknown boards return `BOARD_NOT_FOUND`; omitted reads follow Hermes' current default dynamically. |
| Read authorization | Hermes has no principal ACL to delegate to the MCP, and the requested policy is global read. | Omitted deployment caps expose all active canonical boards to the resource owner; explicit caps remain operational limits and are documented as such. |
| Write authorization | A token must not self-select a second write board. | A write grant carries one signed `board` plus `board_access=write`; another board returns `BOARD_SESSION_MISMATCH`; read-only grants cannot create. |
| Query/command isolation | Reusing the v0.1 read adapter for writes would weaken `mode=ro` guarantees. | Separate `ReadOnlyHermesStore` and `HermesCreateAdapter`; all seven query tools use `mode=ro` plus `PRAGMA query_only=ON`. |
| Public mutation surface | A broad Hermes API or CLI would expose unrelated mutators. | MCP discovery returns exactly eight tools; `create_task` is the only write. No update/delete/claim/assign-after-create/move/start/complete/review/approve/reject/retry/import/sync tool is registered. |
| OAuth persistence | Clients and refresh grants must survive restart, while codes remain ephemeral. | DCR metadata, refresh hashes, board grant records, and revoked grant IDs persist atomically in the mode-0600 state file; access tokens remain signed/self-contained and auth codes remain in memory. |
| MCP annotations | Clients need an explicit distinction between query and additive write. | Seven tools advertise `readOnlyHint=true`; create advertises `readOnlyHint=false`, `destructiveHint=false`, and `idempotentHint=true`. |
| Validation | Unbounded or invented create fields could widen the command surface. | Strict schemas reject extras and bound title/body/parents/IDs/priority; Hermes performs the authoritative normalization and transaction checks. |
| Retry safety | A remote timeout can cause ChatGPT to retry a write. | `idempotency_key` is mandatory and scoped by Hermes to the selected board database. |
| Sandbox | Enabling canonical writes must not make the query path writable. | systemd keeps `ProtectSystem=full`, `ProtectHome=read-only`, `NoNewPrivileges`, write access only to named-board storage, and a private OAuth state directory; the Hermes legacy root DB/WAL files remain outside the MCP boundary. |

## Verification evidence

- Local suite: `63 passed`.
- Compile check: `compileall` passed.
- Multi-board fixture proof: all active fixture boards are discovered, reads are
  isolated, explicit unknown slugs do not fall back, and writes are bound to
  one board per grant.
- OAuth proof: read-only token denial, write-board claims, refresh preservation,
  old-grant rejection after revocation, and state persistence tests pass.
- OCI deployment recheck passed: systemd is active with zero restart loops,
  OpenResty syntax and TLS passed, the service exposes all 12 currently active
  boards for read, and a read-only create probe was denied without a write.
- A fresh interactive ChatGPT authorization after this deployment is not
  inferred from local or service probes; it must be completed before claiming
  live ChatGPT write success.

## Deliberate non-exposure

`add_comment`, task editing, dependencies, lifecycle/controller actions,
dispatch, board administration, tenant administration, and arbitrary filesystem
or database access remain outside the MCP surface. `tenant` and `session_id`
are task metadata only; neither is an authorization selector.

## Known residual risks

- Board reads are global to the configured Hermes resource owner because Hermes
  has no canonical per-principal ACL. A future multi-user deployment needs a
  real Hermes authorization model rather than an MCP-only claim.
- A single systemd instance is supported. Multi-replica create idempotency
  would require shared coordination.
- Existing ChatGPT clients whose DCR metadata or grant contains only
  `hermes:read` need a fresh authorization that requests `hermes:create`;
  clients are never silently broadened.
- OAuth state is local to one systemd instance and has no distributed-store
  semantics.
- HTTPS certificate issuance and renewal remain owned by the existing
  OpenResty/1Panel deployment.
