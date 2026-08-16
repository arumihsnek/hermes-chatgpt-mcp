# OAuth Create Scope Diagnosis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine, with a real post-instrumentation ChatGPT OAuth flow, the first boundary at which `hermes:create` is absent, without changing authorization policy or exposing secrets.

**Architecture:** Add a disabled-by-default diagnostic logger at the existing DCR, authorization-code, token, refresh, and bearer-verification boundaries. It emits only bounded scope metadata and short one-way fingerprints; it does not persist raw protocol values or alter scope decisions. Validate the logger with local OAuth tests, then enable only this flag in the existing systemd service for one controlled fresh ChatGPT authorization.

**Tech Stack:** Python 3.11, Starlette/FastMCP 1.28.1, pytest, systemd journal, JSON OAuth state.

**Spec:** User request for experimental `hermes:create` scope-loss diagnosis on 2026-08-16.

## Global Constraints

- Do not grant or broaden any OAuth scope.
- Do not change `create_task`, board policy, Hermes, or command behavior.
- Never log access tokens, refresh tokens, authorization codes, PKCE values, cookies, Authorization headers, secrets, or raw state-file contents.
- Diagnostic fields are limited to stage, safe fingerprints, bounded known scopes, grant/client reuse metadata, status, and a correlation identifier that is not a credential.
- A real post-instrumentation ChatGPT authorization is required before declaring a root cause.
- Keep the worktree clean before each commit and run `git diff --check`.

---

### Task 1: Establish the baseline and diagnostic contract

**Files:**
- Create: `docs/evidence/OAUTH-CREATE-SCOPE-DIAGNOSIS-2026-08-16.md`
- Modify: `docs/superpowers/plans/2026-08-16-oauth-create-scope-diagnosis.md`
- Test: existing suite, especially `tests/test_auth.py` and `tests/test_oauth_http.py`

**Interfaces:**
- Consumes: current `master` worktree, deployed `hermes-chatgpt-mcp.service`, and sanitized OAuth-state metadata.
- Produces: a baseline record with repo/deployment correspondence and explicit observed-vs-missing evidence sections.

- [x] Verify repository, branch, HEAD, status, worktrees, recent commits, service state, effective unit, process cwd, and source hashes.
- [x] Verify the v0.2 commit is an ancestor of the inspected deployment source and identify the current v0.3 HEAD.
- [x] Run the existing test suite before source changes and record only aggregate results plus failures.
- [x] Create the evidence report with `HECHOS OBSERVADOS`, `AFIRMACIONES PREVIAS`, `INFERENCIAS`, `EVIDENCIA AUSENTE`, `CAUSA RAÍZ`, and `CORRECCIÓN` headings; leave causal fields unconfirmed until the live flow is observed.
- [x] Commit the baseline evidence separately from instrumentation.

### Task 2: Add disabled-by-default safe OAuth diagnostics

**Files:**
- Modify: `hermes_chatgpt_mcp/config.py` to parse a boolean `MCP_OAUTH_DIAGNOSTICS` flag.
- Modify: `hermes_chatgpt_mcp/auth.py` to emit safe events at registration, authorization-code creation/exchange, refresh rotation, and bearer verification.
- Modify: `hermes_chatgpt_mcp/server.py` to emit safe request-stage events for DCR, `/authorize`, `/token`, and MCP requests without logging headers or raw form values.
- Test: `tests/test_auth.py`, `tests/test_oauth_http.py`, and a focused new diagnostic test if needed.

**Interfaces:**
- Consumes: `Settings.oauth_diagnostics`, `AuthService.supported_scopes`, client scope records, `_Code`, `_Refresh`, and verified `AccessToken` values.
- Produces: journal events named `hermes_oauth_diagnostic` with bounded keys: `stage`, `event_id`, `client_fp`, `token_fp` or `refresh_fp` only where necessary for correlation, `requested_scopes`, `allowed_scopes`, `granted_scopes`, `effective_scopes`, `client_reused`, `new_registration`, `http_status`, and `outcome`.

- [x] Write failing tests proving diagnostics are disabled by default and that enabled events contain no raw token/code/PKCE/secret values.
- [x] Write a stable fingerprint and scope-summary helper that uses SHA-256 prefixes and only emits known scope names or a bounded invalid marker.
- [x] Add the minimal diagnostic calls at the OAuth boundaries; keep all existing validation and returned responses unchanged.
- [x] Add MCP bearer verification logging with effective scopes and client fingerprint only when enabled.
- [x] Run focused tests, then the full suite; inspect captured log records for forbidden fields and `git diff --check`.
- [ ] Commit only the diagnostic source and tests.

### Task 3: Enable diagnostics in the existing deployment

**Files:**
- Modify: `deploy/systemd/hermes-chatgpt-mcp.service` to set `MCP_OAUTH_DIAGNOSTICS=1` explicitly as a temporary documented diagnostic flag.
- Modify: `docs/DEPLOYMENT.md` and `docs/SECURITY.md` to describe the flag, safe fields, retention, and removal procedure.

**Interfaces:**
- Consumes: the committed diagnostic flag and existing systemd unit.
- Produces: one restartable service configuration that records the OAuth handshake in the journal without changing scope policy.

- [x] Add a test asserting the unit enables only the diagnostic flag and preserves `NoNewPrivileges`, `ProtectHome`, `ProtectSystem`, and existing paths.
- [x] Commit the deployment/configuration change separately.
- [x] Install/reload only the instrumented unit, restart the existing service, and verify health, PID, cwd, source HEAD, and TLS without printing secrets.
- [x] Confirm diagnostic mode is active through safe process environment metadata.

### Task 4: Run and correlate one fresh ChatGPT authorization

**Files:**
- Modify: `docs/evidence/OAUTH-CREATE-SCOPE-DIAGNOSIS-2026-08-16.md`

**Interfaces:**
- Consumes: journal events from one authorization performed after diagnostics are active.
- Produces: a sanitized chain `DCR -> authorize request -> grant/code -> authorization-code token -> refresh (if used) -> MCP bearer` with scopes at each boundary.

- [ ] Leave the service healthy and request exactly one user action: remove/reconnect the MCP App once so ChatGPT performs a fresh authorization after the diagnostic start time.
- [ ] Capture a bounded journal interval and parse only `hermes_oauth_diagnostic` events; verify no forbidden raw values appear.
- [ ] Correlate events by safe event/fingerprint identifiers and identify the first observed transition where `hermes:create` is absent.
- [ ] If ChatGPT never performs the flow or refresh is not observed, mark the missing segment and use `WAITING_FOR_FRESH_CHATGPT_AUTH` or `INSUFFICIENT_EVIDENCE` rather than infer a cause.
- [ ] Commit the sanitized evidence report only; never commit raw journal or OAuth state.

### Task 5: Decide whether a correction is justified

**Files:**
- Modify only the minimal responsible source/config file if the live chain proves a server-side defect.
- Test: add a regression test at the proven boundary.
- Modify: `docs/evidence/OAUTH-CREATE-SCOPE-DIAGNOSIS-2026-08-16.md`.

**Interfaces:**
- Consumes: the observed causal chain and the smallest failing local reproduction.
- Produces: either no behavior change with an evidence-backed external/client diagnosis, or one narrowly scoped server fix with regression coverage.

- [ ] Do not enter this task unless a real authorization or equivalent trace proves the causal boundary.
- [ ] If the server emits the requested scope correctly, preserve fail-closed behavior and document that the loss is outside this repository.
- [ ] If the server loses the scope, write a failing regression test first, implement one minimal fix, run focused and full tests, and review the security diff.
- [ ] Remove or disable temporary diagnostics after evidence capture unless retention is explicitly required; document the final state.
- [ ] Commit any correction separately from the diagnosis and report the exact final status.

## Self-Review Checklist

- [ ] No raw credential-like value appears in source logs, tests, journal excerpts, or committed evidence.
- [ ] Existing scopes and `create_task` enforcement are unchanged unless a proven root cause requires a minimal correction.
- [ ] DCR client reuse, client scope, authorization grant scope, token scope, refresh scope, and MCP effective scope are independently represented.
- [ ] Missing live evidence is clearly labeled; no root cause is declared from unit tests alone.
- [ ] Tests pass after the final change and `git diff --check` is clean.
