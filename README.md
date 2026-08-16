# hermes-chatgpt-mcp

`hermes-chatgpt-mcp` is a small remote MCP facade for querying the canonical Hermes Kanban state from ChatGPT. It imports Hermes' read/query domain module and exposes bounded projections over authenticated Streamable HTTP.

## v0.1 is READ ONLY

This service cannot create, update, delete, claim, assign, move, start, complete, close, review, approve, reject, retry, import, or sync Hermes state. The public MCP allowlist contains exactly six query tools. Hermes remains the semantic authority for task status, links, runs, dispatch-related fields, evidence, and activity.

## Architecture

```text
ChatGPT web
    │ OAuth 2.1 + PKCE, HTTPS
    ▼
OpenResty /mcp and OAuth paths
    │ loopback 127.0.0.1:8789
    ▼
hermes-chatgpt-mcp (systemd)
    │ mode=ro + PRAGMA query_only=ON
    ▼
Hermes hermes_cli.kanban_db query API
    ▼
Hermes Kanban SQLite/WAL state
```

The reconnaissance and rejected alternatives are recorded in [`docs/architecture/HERMES-INTEGRATION.md`](docs/architecture/HERMES-INTEGRATION.md). The implementation design is in [`docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-design.md`](docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-design.md).

## Requirements

- Python 3.11.
- Hermes installed at `/home/ubuntu/hermes-agent`, or `HERMES_AGENT_ROOT` pointing to the real source tree.
- The service user must be able to read the selected Hermes board.
- Runtime dependencies from `pyproject.toml`; the OCI deployment uses the Hermes virtualenv.

## Configuration

Copy [`.env.example`](.env.example) to a 0600 runtime environment file. At minimum set:

```text
HERMES_AGENT_ROOT=/home/ubuntu/hermes-agent
HERMES_KANBAN_HOME=/home/ubuntu/.hermes
HERMES_KANBAN_BOARD=codex_app_server
MCP_PUBLIC_BASE_URL=https://kanban.hermesinthenight.duckdns.org
MCP_HOST=127.0.0.1
MCP_PORT=8789
MCP_OAUTH_USERNAME=chatgpt
MCP_OAUTH_PASSWORD=<random password, never commit>
MCP_OAUTH_SIGNING_KEY=<random signing key, never commit>
```

Remote origins must use HTTPS. Local development may use `http://127.0.0.1:8789`. Pagination, graph, body, log, activity, OAuth-code, and token bounds are configurable but fail closed when invalid.

## Local execution

```bash
cp .env.example .env
# Replace the two secret placeholders in .env; do not commit it.
set -a; . ./.env; set +a
/home/ubuntu/hermes-agent/venv/bin/python -m hermes_chatgpt_mcp.server
```

The MCP endpoint is `/mcp`; liveness is `/healthz`. OAuth metadata is exposed at `/.well-known/oauth-authorization-server`, and protected-resource metadata is supplied at `/.well-known/oauth-protected-resource`.

## Tests and live proof

The suite includes unit, adapter, contract, OAuth, integration-fixture, and before/after read-only fingerprint tests:

```bash
/home/ubuntu/hermes-agent/venv/bin/python -m pytest -q
/home/ubuntu/hermes-agent/venv/bin/python -m compileall -q hermes_chatgpt_mcp tests scripts
```

The live smoke is opt-in and requires an explicit board; it calls all six canonical operations against the real Hermes installation and checks DB/WAL/metadata fingerprints:

```bash
HERMES_LIVE_TEST=1 \
HERMES_AGENT_ROOT=/home/ubuntu/hermes-agent \
HERMES_KANBAN_HOME=/home/ubuntu/.hermes \
HERMES_KANBAN_BOARD=codex_app_server \
/home/ubuntu/hermes-agent/venv/bin/python scripts/live_smoke.py
```

## MCP tools

- `get_board`: configured board metadata and canonical status/assignee counts.
- `list_tasks`: bounded canonical task listing with status, assignee, tenant, session, archive, limit, and order filters.
- `get_task`: task body and canonical fields, direct parents/children, run summaries, and safe attachment metadata.
- `get_task_graph`: bounded root-centered parent/child graph with explicit truncation.
- `get_dispatch`: deterministic external `READY`, `BLOCKED`, `REVIEW`, or `COMPLETED` projection with reasons and the raw Hermes status.
- `get_activity`: bounded events/ledger, comments, runs/outcomes, worker-log tail, result/summary, and attachment metadata.

The MCP schemas reject unknown fields and bound IDs, filters, page sizes, graph size, body, logs, and activity. Physical DB paths, attachment paths, credentials, and secret-like metadata are not returned.

## Authentication and ChatGPT connection

The remote service requires a bearer token for `/mcp`; anonymous requests receive `401`. OAuth uses public-client registration, authorization code, PKCE S256, short-lived signed access tokens, optional rotated refresh tokens, issuer/audience/expiry/scope validation, and a private login credential supplied only through the environment file. The service advertises `none` as its token endpoint authentication method and does not claim support for client secrets.

In ChatGPT, add a custom connector/MCP connection using the stable HTTPS URL:

```text
https://kanban.hermesinthenight.duckdns.org/mcp
```

Complete the OAuth login when ChatGPT opens the authorization page. The callback must be the URI ChatGPT sends during dynamic registration; the implementation accepts the documented `https://chatgpt.com/connector/oauth/...` callback family through its registered exact redirect URI. OpenAI's current MCP guidance is in [Build an MCP server](https://developers.openai.com/plugins/build/mcp-server) and [Authenticate users](https://developers.openai.com/plugins/build/auth).

## OCI deployment

The reproducible installer targets the existing machine boundary:

```bash
./scripts/install_oci.sh
```

It installs `hermes-chatgpt-mcp.service`, creates/updates the 0600 environment file without printing its values, binds only to loopback port 8789, validates the active 1Panel OpenResty container configuration, reloads the existing OpenResty hook, and checks `/healthz`. The existing TLS host `kanban.hermesinthenight.duckdns.org` keeps its HermesKanban `/` route; only `/mcp`, OAuth metadata/auth/token, and `/healthz` are proxied to this service. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for rollback and verification.

```bash
sudo systemctl status hermes-chatgpt-mcp.service
sudo journalctl -u hermes-chatgpt-mcp.service -f
./scripts/uninstall_oci.sh
```

The installer preserves the runtime environment and timestamped edge backups during rollback. It never modifies Hermes source or Kanban rows.

## Limitations of v0.1

- One configured board is served per process; changing `HERMES_KANBAN_BOARD` requires a service restart.
- OAuth registration/code/refresh state is in memory; a restart requires ChatGPT to authorize again.
- This is a query interface, not a write/control plane, scheduler, notification bridge, or task editor.
- The service depends on the installed Hermes query module and its SQLite schema; a Hermes upgrade should rerun reconnaissance and the live smoke before promotion.
- Public ChatGPT connection still depends on the connector account accepting the configured OAuth callback and the external network/DNS path remaining available.
