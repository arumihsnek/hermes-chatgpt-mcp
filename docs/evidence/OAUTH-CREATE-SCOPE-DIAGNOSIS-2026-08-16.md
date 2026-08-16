# OAuth `hermes:create` scope diagnosis — 2026-08-16

## Status

`WAITING_FOR_FRESH_CHATGPT_AUTH`

No root cause is declared. The required causal chain must include one authorization performed after the safe diagnostics are enabled.

## HECHOS OBSERVADOS

### Repository and deployed process

- Repository: `/home/ubuntu/code/hermes-chatgpt-mcp`.
- Branch: `master`.
- Inspected HEAD: `8b6262524d247246a837d5c106e84beaebaac601`.
- Worktree was clean before instrumentation.
- The v0.2 reference commit `36eaa42a23dd54f21139e8a9d2f75934e28de165` and v0.3 reference commit `94ab3a1b6207ad383cef7673165a1ac6b92f0db8` are ancestors of the inspected HEAD.
- `hermes-chatgpt-mcp.service` is active under systemd, runs with working directory `/home/ubuntu/code/hermes-chatgpt-mcp`, and starts `/home/ubuntu/hermes-agent/venv/bin/python -m hermes_chatgpt_mcp.server`.
- The SHA-256 of the repository unit and `/etc/systemd/system/hermes-chatgpt-mcp.service` matched during inspection.
- The OAuth state file is `/var/lib/hermes-chatgpt-mcp/oauth-state.json`, mode `0600`, with its parent directory mode `0700`.
- Safe diagnostics are deployed from commit `83385d2837da70a3dafede80cda9be898063468c` with `MCP_OAUTH_DIAGNOSTICS=1`; the service restarted successfully at `2026-08-16 18:17:40 UTC`.
- Post-restart checks returned local health `{"status":"ok"}`, public OAuth metadata, and preserved the same three clients and six refresh records with the same scope distribution.
- Since that restart, the service journal contains zero `hermes_oauth_diagnostic` events and zero OAuth access-log lines. No fresh ChatGPT authorization has occurred yet.

### Existing persisted OAuth metadata

The state file contained three client records and six refresh-token records. Only safe metadata was inspected:

- one client record had `hermes:read hermes:create offline_access`;
- two ChatGPT-labelled client records had `hermes:read` only;
- refresh records had five `hermes:read` scopes and one `hermes:read hermes:create offline_access` scope;
- client identifiers were represented only by short one-way fingerprints in the diagnostic notes.

This proves that old read-only client/grant state exists, but does not prove which record the next ChatGPT flow will use.

### Existing journal evidence before instrumentation

The journal contained successful `/oauth/authorize` and `/oauth/token` HTTP requests. Sanitized access-log entries showed `scope=hermes:read` on observed authorization requests. The access logs did not expose the token response scope, so they cannot establish the token-scope transition or correlate it to a subsequent MCP bearer request.

The existing access logger also included OAuth query parameters. No such raw values are copied into this report. The instrumented process disables Uvicorn access logging while the controlled experiment runs; the diagnostic logger emits only bounded metadata and one-way fingerprints.

### Baseline tests

Before source changes: `52 passed`.

After the local diagnostic implementation: `57 passed`.

## AFIRMACIONES PREVIAS

- ChatGPT was reported to have been reinstalled/reconnected and to receive read-only effective capabilities.
- `create_task` was reported to fail with `SCOPE_REQUIRED` and without creating a task.
- Those observations do not identify whether the missing scope originated at DCR, `/authorize`, token issuance, refresh, client/grant reuse, or MCP bearer validation.

## INFERENCIAS

Static source inspection shows this scope flow:

1. DCR validates and persists the client's requested scope.
2. `/authorize` permits only a requested scope contained in the persisted client scope.
3. The authorization code stores the normalized requested scope.
4. The authorization-code token copies the code scope.
5. Refresh rotation copies the persisted refresh-record scope.
6. MCP bearer verification enforces the scopes carried by the access token; `create_task` separately requires `hermes:create`.

This is a code-path description, not experimental proof of what ChatGPT sent or what it used after refresh.

## EVIDENCIA AUSENTE

The following chain has not yet been observed for one fresh ChatGPT authorization after diagnostics start:

```text
ChatGPT /authorize request
  -> granted authorization scope
  -> authorization-code token scope
  -> refresh requested/result scope, if refresh occurs
  -> MCP bearer effective scope
```

Also absent is a post-instrumentation observation proving whether DCR occurred or an existing client identifier was reused.

## DIAGNOSTIC INSTRUMENTATION

The pending diagnostic flag is `MCP_OAUTH_DIAGNOSTICS=1`. When enabled, events use logger name `hermes_chatgpt_mcp.oauth` and event marker `hermes_oauth_diagnostic`. They contain only:

- stage and bounded status/outcome;
- known scope names or an invalid/empty marker;
- short SHA-256 fingerprints of client IDs, codes, tokens, refresh tokens, and flow inputs;
- redirect scheme/host/path without query or fragment;
- safe client/grant reuse booleans.

Raw tokens, refresh tokens, authorization codes, PKCE values, credentials, cookies, Authorization headers, and OAuth state contents are not logged by this instrumentation.

## CAUSA RAÍZ

`NOT_PROVEN`.

## CORRECCIÓN

No OAuth scope policy or permission behavior has been changed. No Hermes code has been modified. The next step is one controlled real authorization after the instrumented service is healthy.
