# Security boundary

## External surface

The only public MCP route is `/mcp`. OpenResty forwards only that exact path, the two OAuth metadata paths, `/oauth/`, and `/healthz` to loopback port 8789. The existing HermesKanban `/` route remains separate. The service does not listen on a public interface.

## Authentication

All MCP requests require a bearer token validated for issuer, audience, expiry, signature, and `hermes:read`. OAuth registration accepts only public `none` clients, exact registered HTTPS redirect URIs (or localhost HTTP for development), authorization code, PKCE S256, and bounded scopes. Login comparisons are constant-time and failure messages are generic. Access and refresh state is short-lived/in-memory and secrets are environment-only.

## Read-only defense in depth

- Adapter imports Hermes query models/functions only.
- Production never calls Hermes `connect`, `init_db`, `write_txn`, dispatch, or command methods.
- SQLite opens `file:...?mode=ro`; the connection immediately enables `PRAGMA query_only=ON`.
- MCP annotations mark every tool `readOnlyHint=true`, `destructiveHint=false`, and `idempotentHint=true`.
- The generated FastMCP argument envelope and nested Pydantic models reject unknown fields.
- The fixture and live tests fingerprint DB/WAL/SHM/metadata before and after all read operations.

## Data minimization

IDs, titles, statuses, bounded bodies, summaries, activity, and safe attachment metadata are returned. Stored filesystem paths, workspace paths, credentials, environment-like metadata, and secret-like fields are removed or redacted. Errors exposed to clients are stable and do not include stack traces.

## Operational controls

Inputs have explicit size/count/depth limits; systemd uses a dedicated unprivileged user, `NoNewPrivileges`, private temporary storage, read-only system/home protections, and journald logs. The selected board directory is writable only as a SQLite coordination exception; query-only mode remains enforced by the application.
