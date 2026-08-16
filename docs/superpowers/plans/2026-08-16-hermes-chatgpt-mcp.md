# Hermes ChatGPT MCP v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independently deployable, authenticated, strictly read-only MCP server that exposes bounded Hermes Kanban queries over Streamable HTTP without reimplementing Hermes domain rules.

**Architecture:** A small Python service imports Hermes' canonical `hermes_cli.kanban_db` read models from the installed Hermes source, opens selected SQLite databases through an explicit `mode=ro`/`query_only` adapter, projects canonical data into stable MCP schemas, and exposes only six query tools. FastMCP provides the MCP transport and bearer-token enforcement; a narrow local OAuth 2.1 authorization-code/PKCE surface supports ChatGPT's remote connector flow. OpenResty terminates HTTPS and proxies only the MCP/auth/health paths to a loopback systemd service.

**Tech Stack:** Python 3.11; `mcp==1.28.1`; FastMCP; Pydantic 2; Starlette/Uvicorn; SQLite read-only URI connections; pytest/pytest-asyncio; systemd; OpenResty.

**Spec:** `docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-design.md`

## Global Constraints

- The integration repository is the only write scope for implementation. Do not edit `/home/ubuntu/hermes-agent`, `/home/ubuntu/code/HermesKanban`, or live Hermes data.
- Never call `hermes_cli.kanban_db.connect`, `init_db`, `write_txn`, `dispatch_once`, or any mutating task/board API from production code.
- Every database connection must use SQLite URI `mode=ro` and immediately enable `PRAGMA query_only=ON`; do not use `immutable=1` because Hermes boards may have WAL sidecars.
- All public inputs and outputs are bounded. Pydantic models must reject unknown fields and invalid enum values.
- The public tool set is exactly six tools: `get_board`, `list_tasks`, `get_task`, `get_task_graph`, `get_dispatch`, and `get_activity`.
- No tool may expose write verbs or call equivalents such as create, update, delete, claim, assign, move, start, complete, close, review, approve, reject, retry, import, or sync.
- Secrets are supplied only through runtime environment files; no secret values may enter source, tests, fixtures, logs, snapshots, or command output.
- Keep the service stateless at the HTTP layer where practical and fail closed on missing configuration, invalid authentication, invalid board selection, and oversized requests.
- Preserve the dirty Hermes checkout and verify its HEAD/status before and after live reconnaissance.

## Task 1: Establish project metadata and dependency contract

**Files:** `pyproject.toml`, `.env.example`, `Makefile`, `hermes_chatgpt_mcp/__init__.py`, `scripts/run_local.sh`.

- [ ] Add package metadata, Python requirement, pinned runtime dependencies compatible with the Hermes venv, test/lint configuration, and an explicit package entry point.
- [ ] Add a non-secret environment template documenting required production variables and safe local defaults.
- [ ] Add make targets for test, lint, format-check, local server, and live smoke; ensure commands use the configured Hermes Python when available.
- [ ] Add the package version and a short read-only service description.
- [ ] Verify `python -m compileall` and dependency imports before moving to service code.

## Task 2: Add failing fixture and read-only storage tests first

**Files:** `tests/conftest.py`, `tests/fixtures.py`, `tests/test_readonly_storage.py`.

- [ ] Build a temporary Hermes-shaped SQLite fixture using the canonical Hermes schema text only for test data creation; include boards metadata, tasks across statuses, parent/child links, events, comments, runs, attachments, and a worker-log fixture.
- [ ] Add a database fingerprint helper that records file bytes plus WAL/SHM sidecar metadata where present without mutating the database.
- [ ] Write tests proving the adapter opens an existing DB without creating files, sets `query_only`, rejects an attempted write, and leaves the fingerprint unchanged.
- [ ] Write tests proving missing boards and path traversal candidates are rejected before opening a database.
- [ ] Run the focused tests and capture the expected red failure because the adapter does not yet exist.

## Task 3: Implement configuration and canonical Hermes read adapter

**Files:** `hermes_chatgpt_mcp/config.py`, `hermes_chatgpt_mcp/hermes.py`, `tests/test_config.py`, `tests/test_readonly_storage.py`.

- [ ] Implement typed settings with strict bounds for board slug, page size, graph depth/node count, body/log/event sizes, OAuth values, host/port, and public URL.
- [ ] Resolve Hermes source from `HERMES_AGENT_ROOT` and import only the canonical `hermes_cli.kanban_db` module; fail clearly if it is unavailable.
- [ ] Resolve the default/named board using Hermes' documented `kanban_home`, `boards_root`, `get_current_board`, `board_exists`, and `kanban_db_path` read paths without invoking initialization.
- [ ] Implement a context-managed read-only connection using the existing tracked-read helper when available, SQLite URI `mode=ro`, `row_factory=sqlite3.Row`, and immediate `PRAGMA query_only=ON`.
- [ ] Expose only a small `ReadOnlyHermesStore` protocol with query methods needed by the adapter; keep SQLite/path details behind this boundary.
- [ ] Add tests for environment parsing, default board resolution, named board resolution, path rejection, WAL-safe read opening, and no-write fingerprint invariants.
- [ ] Run the storage/config tests to green and inspect the diff for any writable Hermes call.

## Task 4: Implement stable schemas, projections, and deterministic dispatch

**Files:** `hermes_chatgpt_mcp/schemas.py`, `hermes_chatgpt_mcp/dispatch.py`, `hermes_chatgpt_mcp/adapter.py`, `tests/test_dispatch.py`, `tests/test_adapter.py`.

- [ ] Define strict Pydantic request models for the six tools, including bounded pagination, status/assignee/tenant/session filters, graph depth, and activity limits.
- [ ] Define output models that preserve canonical raw task status while adding stable board/task/graph/activity projections; redact physical paths and cap body/log/metadata payloads.
- [ ] Implement `get_board` from Hermes board metadata/stats and bounded task summaries, without inventing board state.
- [ ] Implement `list_tasks` by delegating filtering/order semantics to Hermes' canonical `list_tasks` and applying only response bounding/serialization.
- [ ] Implement `get_task` from canonical task, graph context, runs, result, and summary readers; return a sanitized not-found error for unknown IDs.
- [ ] Implement `get_task_graph` with canonical parent/child/link readers, cycle protection, depth/node caps, and explicit truncation metadata.
- [ ] Implement `get_activity` from canonical events/comments/runs/summary/result/attachment/log readers; never return stored filesystem paths or unbounded log content.
- [ ] Implement dispatch as a pure projection over canonical status, dependencies, claim/run fields, and failure/block metadata. The projection must emit one deterministic external state (`READY`, `BLOCKED`, `REVIEW`, or `COMPLETED`) plus reasons; represent currently `running` tasks explicitly without relabeling them as ready.
- [ ] Add unit tests for every status, dependency gate, claim gate, failure reason, truncation path, ordering/filter path, graph cycle guard, and not-found case.
- [ ] Run all adapter/projection tests to green.

## Task 5: Add authenticated FastMCP service and contract tests

**Files:** `hermes_chatgpt_mcp/auth.py`, `hermes_chatgpt_mcp/server.py`, `tests/test_auth.py`, `tests/test_mcp_contract.py`.

- [ ] Implement a bounded in-memory OAuth 2.1 authorization-code flow with PKCE S256, dynamic registration restricted to public `none` clients, HTTPS/localhost redirect validation, short-lived single-use codes, and signed short-lived bearer tokens scoped to `hermes:read`.
- [ ] Implement OAuth metadata routes and use FastMCP's protected-resource middleware/token verifier; ensure metadata advertises the supported auth method honestly and never falls back to anonymous access.
- [ ] Implement constant-time credential verification from environment configuration, generic login failures, no credential logging, and strict issuer/audience/expiry/scope checks.
- [ ] Construct a stateless FastMCP Streamable HTTP app at `/mcp`, register exactly six tools, add explicit read-only/destructive annotations, and add a minimal unauthenticated `/healthz` that reveals no configuration or Hermes data.
- [ ] Convert adapter exceptions to stable JSON-RPC/tool errors without stack traces; reject malformed JSON, unknown fields, oversized inputs, invalid IDs, and unbounded pagination.
- [ ] Add ASGI contract tests for metadata, DCR, PKCE success/failure, token verification, missing/invalid bearer tokens, health, tool listing, exact tool names, schemas, annotations, and sanitized errors.
- [ ] Run the auth and MCP contract tests to green.

## Task 6: Prove every MCP operation is read-only

**Files:** `tests/test_mcp_readonly.py`, `scripts/live_smoke.py`.

- [ ] Invoke every MCP tool against the representative fixture and compare database/data-directory fingerprints before and after each operation.
- [ ] Assert no mutation API names are imported/called by the production adapter and no writable SQLite connection is created.
- [ ] Add a live smoke script that selects the actual current Hermes board, calls all six adapter operations against the real Hermes installation, reports counts and tool names only, and repeats the fingerprint check; it must refuse to run if the source/board paths are ambiguous.
- [ ] Run the full fixture suite and then run the live smoke against `/home/ubuntu/hermes-agent` and the live board without changing Hermes state.

## Task 7: Add reproducible systemd/OpenResty deployment

**Files:** `deploy/systemd/hermes-chatgpt-mcp.service`, `deploy/openresty/kanban-mcp-locations.conf`, `scripts/install_oci.sh`, `scripts/uninstall_oci.sh`, `docs/DEPLOYMENT.md`.

- [ ] Add a least-privilege systemd unit bound to loopback on an unused port, using the Hermes venv, a 0600 environment file, restart-on-failure, private temporary storage, read-only home/system protections compatible with Hermes DB reads, and journald logging.
- [ ] Add an OpenResty include containing only `/mcp`, OAuth metadata/auth/token, and `/healthz` proxy locations, with HTTP/1.1 streaming, buffering disabled, authorization forwarding, bounded timeouts, and no broad proxy to internal Hermes services.
- [ ] Add an idempotent installer that validates paths and ownership, creates/permissions the secret env file without printing its values, installs/enables/restarts the unit, validates local health, validates OpenResty syntax before reload, and preserves a timestamped backup of any edited edge config.
- [ ] Add an uninstall/rollback script that stops/disables only this service and removes only the integration's owned include/marker; never delete Hermes data or unrelated units.
- [ ] Document the existing OCI edge/certificate boundary, deployment variables, service checks, logs, rollback, and the fact that the first deployment may reuse the existing `kanban.hermesinthenight.duckdns.org` certificate via path routing.
- [ ] Validate the unit with `systemd-analyze verify`, the proxy include syntax with the installed OpenResty binary, and local loopback health before any edge reload.

## Task 8: Complete README, review, and final verification

**Files:** `README.md`, `docs/architecture/HERMES-INTEGRATION.md`, `docs/SECURITY.md`, `docs/REVIEW.md`.

- [ ] Replace the scaffold README with architecture, requirements, local setup, configuration, tests, tools, authentication, ChatGPT connector steps, OCI deployment, limits, and an unmistakable `v0.1 = READ ONLY` statement.
- [ ] Add a security note covering OAuth/PKCE, secret handling, bounds, error redaction, path isolation, and the six-tool allowlist.
- [ ] Perform an independent review for Hermes canonicality, accidental mutation, schema quality, auth, deployment, logs, and test coverage; record findings and resolutions.
- [ ] Re-run focused tests, full tests, lint/format/compile checks, live read-only smoke, service health, and (if deployed) public HTTPS metadata/MCP checks.
- [ ] Verify `git status`, `git diff --check`, no secret-like assignments in tracked files, no changes in Hermes, and a clean semantic commit history.
- [ ] Only then report `PASS`; if OCI HTTPS or live external ChatGPT connectivity remains unavailable, report `PARTIAL` with exact evidence and the next safe step.

## Verification Commands

Run from `/home/ubuntu/code/hermes-chatgpt-mcp` with `/home/ubuntu/hermes-agent/venv/bin/python`:

```bash
/home/ubuntu/hermes-agent/venv/bin/python -m pytest -q
/home/ubuntu/hermes-agent/venv/bin/python -m compileall -q hermes_chatgpt_mcp tests scripts
git diff --check
git status --short
```

Use the live command only after fixture tests pass and only with explicit read-only environment checks:

```bash
HERMES_LIVE_TEST=1 /home/ubuntu/hermes-agent/venv/bin/python scripts/live_smoke.py
```
