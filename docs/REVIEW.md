# Independent final review

Review date: 2026-08-16 UTC

## Result

The selected boundary is a read-only external facade over Hermes' canonical query module. No Hermes repository file was modified. The service is deployed independently and the public HTTPS endpoint was exercised against the live Hermes board.

## Findings and resolutions

| Area | Finding | Resolution/evidence |
| --- | --- | --- |
| Canonicality | Hermes' dashboard and existing MCP/tool surfaces contain mutation routes. | Rejected them; adapter calls only `hermes_cli.kanban_db` query readers and the live smoke passed against `codex_app_server`. |
| Read-only storage | Hermes' normal `connect()` performs initialization/migration work. | Never call it; use URI `mode=ro`, tracked connection when available, and `PRAGMA query_only=ON`. Fixture SQL writes fail and all six MCP calls preserve the fingerprint. |
| WAL/systemd | `ProtectHome=read-only` prevented SQLite WAL/SHM reads in the service namespace. | Added a board-specific `ReadWritePaths` coordination exception while retaining application query-only mode; live public calls now pass. |
| MCP surface | FastMCP 1.28.1's generated outer argument model ignored unknown fields. | Rebuilt the pinned SDK's outer models with `extra=forbid`; contract tests assert the exact six tools and read-only annotations. |
| Authentication | Built-in FastMCP OAuth metadata advertises client-secret methods that do not match the ChatGPT connector contract. | Custom bounded DCR/authorize/token routes advertise public `none`, PKCE S256, issuer/audience/scope validation, and bearer enforcement. Public OAuth flow passed. |
| External edge | 1Panel OpenResty is containerized; host `nginx.service` is unrelated/failed. | Installer detects the OpenResty container, validates its actual binary, uses the existing reload hook, and proxies only the MCP/OAuth/health allowlist. |
| TLS | Existing Kanban fullchain contained only the leaf certificate. | Backed up the shared certificate, restored the official YE1/cross-signed chain, reloaded OpenResty, and verified `openssl` return code 0 plus CA-valid HTTPS metadata/health. |
| Data minimization | Attachment and workspace paths could leak physical filesystem details. | Output models omit them; metadata/log/error fields are bounded and secret-like keys are filtered. |
| Operations | Initial service health check raced process startup. | Installer now retries loopback health and restarts idempotently before the OpenResty reload. |

## Verification evidence

- Fixture suite: `25 passed`.
- Live adapter smoke: six canonical read operations, `codex_app_server`, fingerprint unchanged.
- Public MCP: `initialize`, `tools/list` returned exactly 6, and all six `tools/call` operations succeeded over HTTPS; live fingerprint unchanged.
- Public OAuth: dynamic registration `201`, authorization form `200`, approval redirect `303`, token `200`, rotated refresh token present.
- Service: `systemd-analyze verify` clean for this unit, enabled and active.
- Edge: OpenResty container `openresty -t` successful after deployment.
- HTTPS: `/healthz`, protected-resource metadata, and authorization-server metadata returned `200` with CA-valid TLS.
- Secret scan: no private key, bearer token, or runtime credential file is tracked; `.env` patterns are ignored.

## Remaining risks accepted for v0.1

- OAuth client/code/refresh state is in memory and is lost on restart.
- The board-specific SQLite sidecar exception must be updated if the configured board changes.
- The service has no write capability, revocation UI, audit ledger of connector reads, or ChatGPT web end-to-end account confirmation.
- The deployment depends on the existing 1Panel/OpenResty reload hook and certificate renewal process; the installer validates these prerequisites but does not own certificate issuance.
