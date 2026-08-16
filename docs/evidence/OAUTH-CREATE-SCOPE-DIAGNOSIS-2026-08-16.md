# OAuth `hermes:create` scope diagnosis — 2026-08-16

## Status

`ROOT_CAUSE_CONFIRMED_NOT_FIXED`

The fresh ChatGPT authorization was observed with safe diagnostics enabled. The
server did not receive `hermes:create` in the authorization request. The
existing read-only client record was reused, and the server faithfully carried
the read-only scope through consent and authorization-code token issuance. No
OAuth token was upgraded automatically. A server-side interoperability fix is
now deployed, but a complete post-fix ChatGPT token and `create_task` call are
still pending.

## HECHOS OBSERVADOS

### Repository and deployed process

- Repository: `/home/ubuntu/code/hermes-chatgpt-mcp`.
- Branch: `master`.
- Inspected HEAD after diagnostic deployment: `31ec72203383f418dfb4a4c3668fd7faaa1f6005`.
- Worktree was clean after the diagnostic commits.
- The v0.2 reference commit `36eaa42a23dd54f21139e8a9d2f75934e28de165` and v0.3 reference commit `94ab3a1b6207ad383cef7673165a1ac6b92f0db8` are ancestors of HEAD.
- `hermes-chatgpt-mcp.service` is active under systemd, uses working directory `/home/ubuntu/code/hermes-chatgpt-mcp`, and starts `/home/ubuntu/hermes-agent/venv/bin/python -m hermes_chatgpt_mcp.server`.
- The repository unit and `/etc/systemd/system/hermes-chatgpt-mcp.service` had the same SHA-256 during deployment verification.
- The OAuth state file is `/var/lib/hermes-chatgpt-mcp/oauth-state.json`, with mode `0600`; its parent directory has mode `0700`.
- Safe diagnostics were active with `MCP_OAUTH_DIAGNOSTICS=1`; the service restarted successfully at `2026-08-16 18:17:40 UTC`.
- Health and public OAuth metadata checks passed after restart.

### Existing persisted OAuth metadata

Only safe metadata was inspected. No token, code, verifier, cookie, header, or
raw state content was printed or stored in this report.

After the fresh authorization:

- client records: `3`;
- refresh records: `7` (previously `6`);
- client fingerprint `953e5772616e`: `hermes:read`;
- another read-only client fingerprint: `c7819a4b406b`;
- the only full-scope client fingerprint: `daec45dba293`, with `hermes:read hermes:create offline_access`;
- refresh-scope distribution: `6 × hermes:read`, `1 × hermes:read hermes:create offline_access`.

The client fingerprint used by the fresh authorization was `953e5772616e`,
which already existed in the persisted state and was read-only.

### Fresh authorization chain

The service journal contained six reconstructed diagnostic events for one flow,
identified only by the safe flow fingerprint `fca6c12a9921` and client
fingerprint `953e5772616e`. Journald had split the JSON log records into
bounded fragments; the fragments were reassembled by PID/stream/sequence
without retaining secrets.

| Stage | Observed safe scope result |
|---|---|
| DCR | No DCR request/response event; an existing client was used |
| `/authorize` request | `requested_scopes = hermes:read` |
| consent/grant | `granted_scopes = hermes:read` |
| `/authorize` response | approved, HTTP `303`, `hermes:read` |
| authorization-code token | `effective_scopes = hermes:read`, `granted_scopes = hermes:read` |
| token response | HTTP `200`, new refresh record issued with `hermes:read` |

`hermes:create` is absent from every observed scope field in this flow. The
new refresh record is evidence of refresh-token issuance, not evidence of a
refresh exchange. No refresh request/exchange event occurred in this journal
window.

### MCP request observation

Two `mcp.bearer` diagnostic events were emitted with `outcome=accepted` for the
same client fingerprint `953e5772616e` and the same token fingerprint
`77159e8b2481` as the authorization-code token event above. The user then
confirmed that `get_board()` succeeded. This correlates the freshly issued
read-only token with the live MCP request path.

The `effective_scopes` key in the bearer diagnostic line was not reconstructed
verbatim because a journald fragment was interleaved with an unrelated source
location fragment. The token fingerprint correlation is intact, and the same
token's authorization-code issuance is explicitly recorded with
`effective_scopes=hermes:read`. No secret was exposed by this logging defect.

No refresh-token exchange occurred in the captured journal window. The earlier
real ChatGPT call that returned `SCOPE_REQUIRED: hermes:create` is consistent
with this same read-only authorization, but it predates the correlated bearer
events.

### Fresh DCR attempt after selecting DCR

A later attempt did perform DCR. Two safe diagnostic sequences show the same
behavior for two newly issued client fingerprints:

```text
DCR request       requested_scopes = hermes:read
DCR response      granted_scopes   = hermes:read, HTTP 201
/authorize        requested_scopes = hermes:read hermes:create offline_access
/authorize result invalid_scope, HTTP 400
```

The server's public metadata advertised `hermes:create` and
`offline_access`, but the newly registered client was persisted with only
`hermes:read`. `/authorize` correctly applies the client-specific allowlist and
rejects the later request for scopes outside that allowlist. No authorization
code, access token, refresh token, or MCP request was produced by this failed
attempt.

This is direct evidence that the DCR request sent by ChatGPT did not include
`hermes:create`; it is not evidence that the server's global supported-scope
metadata is missing that scope.

## AFIRMACIONES PREVIAS

- ChatGPT was reported to expose the eight MCP tools and to show `create:false`
  for the visible boards.
- `create_task` was reported to fail with `SCOPE_REQUIRED` without creating a
  task.
- Disconnecting and reconnecting the App did not remove the server-side DCR
  client registry.

Those observations motivated the controlled experiment; the scope transition
above is the direct evidence for this diagnosis.

## INFERENCIAS

The causal chain supported by the fresh evidence is:

```text
ChatGPT used an existing read-only client
  -> /authorize requested only hermes:read
  -> server granted only hermes:read
  -> authorization-code token carried only hermes:read
  -> newly issued refresh record carried only hermes:read
```

The DCR-selected retry adds a second, independently observed chain:

```text
DCR requested hermes:read
  -> client registered with hermes:read
  -> /authorize requested hermes:read hermes:create offline_access
  -> server rejected the client-scope mismatch as invalid_scope
```

This identifies both:

- A: `hermes:create` was not present in the scope received at `/authorize`;
- D, at least for the client: an existing persisted client with read-only
  allowed scopes was used instead of a new DCR registration.

The DCR retry additionally shows B in the narrow, expected sense: the server
received `hermes:create` at `/authorize` but correctly rejected it because the
registered client allowed only `hermes:read`. This is client-scope validation,
not an unexplained server-side loss.

The evidence does **not** show C (loss during refresh), because no refresh
exchange was observed.

The bearer stage is now observed as an accepted request using the same token
fingerprint as the read-only authorization-code token. The direct bearer log
field is subject to the journald interleaving limitation described above.

## FIRST POINT WHERE `hermes:create` DISAPPEARS

For the original reused-client flow, the first observable point was the
incoming `/authorize` request: `hermes:create` was already absent.

For the DCR-selected retry, `hermes:create` was absent from the DCR client's
persisted scope. It appeared in `/authorize`, but authorization correctly
failed with `invalid_scope` because the client had been registered only for
`hermes:read`.

## CAUSA RAÍZ

The deployed server has two observed paths to the same outcome:

1. With the old client, ChatGPT reused a persisted client whose allowed scope
   was `hermes:read` and requested only `hermes:read` at `/authorize`.
2. With DCR selected, ChatGPT registered a new client whose requested and
   granted scope was still only `hermes:read`, then requested
   `hermes:read hermes:create offline_access` at `/authorize`.

In both cases, `hermes:create` was absent from the client scope before token
issuance. The server correctly refused to grant a scope outside that
client-specific allowlist. Reconnecting the App or selecting DCR did not cause
ChatGPT's DCR request to include `hermes:create`.

This is not evidence of a server-side scope-loss bug. The server behaved
fail-closed and did not grant `hermes:create` without receiving it in the
authorization request and without a client record allowing it.

## DIAGNOSTIC INSTRUMENTATION

The diagnostic flag is `MCP_OAUTH_DIAGNOSTICS=1`. Events use logger name
`hermes_chatgpt_mcp.oauth` and marker `hermes_oauth_diagnostic`. They contain
only bounded stages/outcomes, known scope names, short one-way fingerprints,
and redirect identity without query/fragment. Uvicorn access logging was
disabled for the experiment so OAuth query strings were not duplicated into
the journal.

Raw tokens, refresh tokens, authorization codes, PKCE values, credentials,
cookies, Authorization headers, and OAuth state contents are not logged by
this instrumentation.

## CORRECCIÓN

Commit `02d6826` changes the authorization boundary so DCR `scope` metadata is
the client's default scope, not a maximum scope. `/authorize` now accepts only
scopes in the server's global advertised set, and only the explicitly
requested/approved scopes enter the authorization code and token.

The fix was deployed by restarting the existing systemd service. A live GET to
`/oauth/authorize` using the previously read-only persisted client and
`hermes:read hermes:create offline_access` returned HTTP `200` with the
authorization form. No `invalid_scope` event followed that request.

The server was not changed to issue `hermes:create` by default, and
`hermes:read` remains insufficient for `create_task`. No client records were
upgraded in storage and no Hermes code was modified.

The DCR registration request does not need to include the write scope when the
client later requests it explicitly at `/authorize`. The authorization server
still never grants an unrequested scope, and DCR does not default to
`hermes:create`.

## EVIDENCIA AUSENTE

- A refresh-token exchange for this exact flow.
- A directly reconstructable `effective_scopes` field from the bearer event;
  its token fingerprint and prior token issuance are reconstructable.
- A successful DCR request from ChatGPT that includes `hermes:create`.
- Evidence that a grant was reused independently of the reused client; the
  client reuse is proven by the persisted fingerprint and the authorization
  event, but no separate grant-reuse flag was emitted.

These absences do not change the first disappearance point: the scope was
already missing from the client metadata in the original DCR/reuse flows; the
post-fix authorization boundary now accepts the later explicit request.

## TESTS AND DEPLOYMENT CHECKS

- Baseline before source changes: `52 passed`.
- After safe instrumentation: `57 passed`.
- After the scope-boundary correction: `59 passed`.
- `git diff --check`: passed.
- `systemd-analyze verify deploy/systemd/hermes-chatgpt-mcp.service`: exit `0`;
  unrelated warnings referred to pre-existing external units.
- Local health endpoint: passed.
- Live `/oauth/authorize` with the existing client and full requested scope:
  HTTP `200` after the correction.
- Public OAuth metadata: passed and advertised `hermes:read`, `hermes:create`,
  and `offline_access`.
