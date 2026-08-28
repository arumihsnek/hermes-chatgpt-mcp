# Recovery truth sync — 2026-08-24

Status: **DOWNSTREAM FROZEN / RECOVERY NEEDS_CHANGES**.

This is a current-state checkpoint. It does not convert an invalid historical
event into an accepted recovery and does not authorize runtime mutation.

## Classification

### Historical event

- `t_64d182d4` / run 1059 was a coder-created recovery mutation with no
  parents and no fresh typed Human Gate. It executed `git reset --hard` to
  `165d1849…` and auto-accepted snapshot substitutes.
- Its recorded `head_after` ending in `...a7b2` conflicts with the authoritative
  Git SHA `165d1849e25c7653a4c1879ca8410475eb8a7d52`.
- `t_39f18334` is revoked historical authorization and cannot authorize this
  event retroactively.
- The old 2026-08-23 snapshots were pruned; their equivalence is not proven.

### Current state

- Hermes Core: exact `165d1849e25c7653a4c1879ca8410475eb8a7d52`; clean porcelain.
- Active tasks and task runs: zero.
- Protected downstream remains frozen; no V4, deploy, restart, update, or
  reparent has occurred.
- Fresh recovery acceptance remains pending and is not accepted.

### Forward mitigations prepared

- Append-only/pinned rollback baseline:
  `/home/ubuntu/.hermes/kanban/runtime-snapshots/recovery-baselines/20260824T190000Z-165d1849-pinned`
  with PIN SHA256
  `8582b93d376cf347414bc2cfa23ccc16d03e7bf5ec1357b23f1240d18b6c7978`.
  Its payload is outside generic `state-snapshots` retention; retirement
  requires an explicit gate.
- Fresh adoption Human Gate: `t_c7bc15c6`, candidate-bound to 165d and the
  pinned baseline. It is pending and explicitly does **not** authorize,
  accept, or repair `t_64d182d4`.
- Fresh acceptance generation: `t_d469c26c`, with fresh authority, rollback,
  and adoption-gate parents. It cannot be accepted until all parents and the
  MCP write disposition pass.

## MCP connector boundary

The public write failure was a real backend `ModuleNotFoundError: yaml`:

`public MCP → create_task(arguments.request) → command adapter →
hermes_cli.kanban_db → hermes_cli.config → yaml`

The running service used an editable package from a beta worktree while the
service venv lacked PyYAML. The prior adapter-only PASS was rejected.

A non-deployed immutable candidate is prepared:

- source commit: `dc25e8bf7a66be87e12da33613d83c874be50038`;
- wheel SHA256:
  `56b7b7f501eab2f3d1f0625af91c3dfe7185df16adeb8c571f4d169e34622a07`;
- `PyYAML==6.0.3` is pinned;
- the effective stable runtime is `/opt/venvs/hermes-chatgpt-mcp/bin/python`;
  the installer validates exact source and wheel hashes, installs into that
  venv, and rejects an editable install;
- service working directory is no longer the mutable source worktree;
- public-like disposable E2E passes OAuth register/authorize/token, MCP
  initialize, tools/list, `create_task(arguments.request)`, and get_task
  readback.

No installation or restart has occurred. The installation/restart Human Gate
must bind source SHA, candidate wheel SHA, rollback wheel SHA, and the named
stable service before use.

## Open P0/P1 boundaries

- **Hermes Core:** authority/executor enforcement, first-side-effect
  authorization consumption, explicit blocked state, and snapshot pinning.
- **Connector/MCP:** wheel/runtime identity, PyYAML parity, and public E2E
  write/readback. OAuth/DCR disposable-client revoke/prune remains open.
- **Orchestration/control plane:** no recovery mutation may become READY
  without a typed authority edge and candidate-bound gate; stale or revoked
  artifacts are evidence only, never authority.
- **V4/post-V4:** this recovery is pre-acceptance. No V4 cut, promotion, or
  downstream reparent is valid until fresh recovery `ACCEPT`.

## Evidence and terms

Primary local evidence is under
`/home/ubuntu/evidence/recovery-20260824/`, including the controller report,
authority audit, snapshot forensic report, MCP E2E report, dispatch-stop
report, baseline pin, and candidate report. `PASS` means the named property
was independently verified; `integrity` alone does not mean equivalence;
historical, resolved, mitigated, OPEN-P0, and NOT_PROVEN remain distinct.
