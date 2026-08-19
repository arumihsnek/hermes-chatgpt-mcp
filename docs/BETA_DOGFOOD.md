# Beta dogfood runbook

This is the controlled real-use gate for
`https://kanban-beta.hermesinthenight.duckdns.org/mcp`. It is separate from
the stable endpoint and does not turn the stable service into beta.

## Connect

Create or reconnect the beta ChatGPT connector and select the board before
requesting command scopes. For normal task dogfood use:

- `hermes:read`
- `hermes:create`
- `hermes:manage`

The selected board must be the board the user intends to manage. `get_board`
must report `read: true`, `create: true`, and `manage: true` before any write.
If either command capability is false, stop as `AUTH_READ_ONLY`; do not retry
the write with different arguments.

`hermes:admin` is an elevated consent and is not needed for ordinary task
creation, comments, links, or workflow management. Grant it only for an
explicit, separately controlled test of filesystem-sensitive, destructive, or
runtime operations.

## Release preflight

The operator verifies the exact candidate after deployment without using a
token:

```bash
python scripts/verify_beta_release.py \
  --url https://kanban-beta.hermesinthenight.duckdns.org \
  --commit "$CANDIDATE_SHA"
```

The result must attest `status=ok`, `surface=beta`, and the exact candidate
SHA. The health projection contains no credentials or filesystem paths.

Then the connector must rediscover the MCP tools. The backend contract for
`notify-subscribe.delivery` is the closed set `notify`, `notify+wake`, `wake`,
or `null`. If ChatGPT displays `string | null` instead, classify it as
`CONNECTOR_DISCOVERY_STALE`; do not change backend scopes or schemas solely on
that stale client observation.

## Safe dogfood boundary

Use a fresh tenant and idempotency keys for test cards. Verify readback after
each mutation and finish with no active claims, runs, links, or notification
subscriptions. Keep the canonical fixture
`hermes-chatgpt-e2e-20260818t224300z` isolated from unrelated dogfood data.

Historical activity, including `Unknown skill(s): sdlc-review`, is not a new
failure. Only a claim, spawn, or run created after the current run begins is
evidence for a current dispatcher incident.

Safety rule: do not run real `boards-rm`, `attach-rm`, `gc`, `repair`, `swarm`, `decompose`,
or dispatch/daemon controls in an ordinary dogfood session. Do not use shell,
SQL, arbitrary paths, raw commands, or invented attachment paths. Elevated
operations remain fail-closed.

## Failure vocabulary

- `AUTH_READ_ONLY`: OAuth grant lacks selected-board create/manage access.
- `BLOCKED_PLATFORM`: a discovered recipient cannot be resolved or the
  connector reports `No functions matching query`.
- `CONNECTOR_DISCOVERY_STALE`: the client schema is older than the public
  backend schema; verify the public health and tools surface independently.
- `NEEDS_CHANGES`: a new backend or deployment defect is reproduced with
  exact evidence.

Do not report `51/51 PASS` from discovery alone. Record the exact SHA, public
health result, tool discovery result, scopes, changed data, and remaining
unexecuted elevated leaves.
