# Beta Dogfood Stability Design

**Status:** approved 2026-08-19

## Goal

Make the public beta suitable for controlled real dogfood with verifiable
release provenance, a repeatable deployment check, and explicit OAuth and
scope guidance, without weakening elevated-scope protections or changing the
canonical 51-leaf surface.

## Observed baseline

- `beta/board-management` is deployed from `d880685f182d6c6aaf8a432ac94684f342942935`.
- The service uses the dedicated beta worktree and Python runtime.
- The full local suite is green at 180 tests.
- The beta runtime publishes the closed `notify-subscribe.delivery` enum.
- ChatGPT connector discovery has independently shown a stale generic schema;
  this is treated as an integration/cache issue, not a reason to alter the
  already-correct backend model.

## Non-goals

- No new generic command, shell, SQL, argv, or raw-command surface.
- No scope reduction for `hermes:admin` operations.
- No automatic reviewer/worker repair based only on historical evidence.
- No destructive cleanup of existing boards, tasks, or subscriptions.
- No claim that destructive or worker-launching leaves are dogfood-tested by
  read-only evidence.

## Design

### 1. Immutable release metadata

The beta deployment writes a small JSON release manifest under its existing
state directory. It contains only the deployed commit SHA, surface name, and
UTC deployment timestamp. The service reads this optional manifest at startup;
it never exposes credentials, filesystem paths, or environment contents.

The public `/healthz` response adds a bounded `build` object while retaining
`status: "ok"`. Local development without a manifest remains usable, but the
beta installer fails closed if the manifest does not report the requested SHA.

### 2. Deployment provenance gate

The versioned systemd unit declares the metadata path. The beta installer
writes the manifest before restart, waits for loopback health, and verifies
that the health response contains the exact candidate SHA and `surface:
"beta"`. This makes a successful deployment and its remote readback
machine-checkable.

### 3. Repeatable dogfood probe

Add a no-secret release verification script that checks a supplied health URL
against an expected commit and beta surface. It is suitable for the public
hostname after deployment and prints only status, surface, and SHA.

### 4. Dogfood documentation

Document the current OAuth flow: select the board before requesting command
scopes, use `hermes:read` plus the needed create/manage scopes, and reserve
`hermes:admin` for explicit elevated tests. Document the read-only gate,
connector-schema-stale classification, and the safe boundaries for workers,
destructive maintenance, and filesystem operations.

## Acceptance criteria

1. New release metadata tests fail before implementation and pass afterward.
2. Health metadata is bounded, deterministic in tests, and contains no secret
   or path fields.
3. Installer tests prove the service, installer, metadata path, and dedicated
   runtime agree.
4. The public verification script rejects a wrong SHA or non-beta surface.
5. Full repository tests, compile checks, shell syntax, and diff checks pass.
6. The deployed service is active, public health returns the exact candidate
   SHA, and the worktree/remote are clean and aligned.
7. Elevated scopes and the canonical tool surface remain unchanged.
