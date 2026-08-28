# V4 Evidence and Open Questions

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE + **V4 STABLE ACCEPTED 2026-08-27**
**Last reconciled:** 2026-08-19 (canonical design) + **2026-08-21 release-candidate truth-sync** (see [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md)) + **2026-08-25 DAG soft-retire contract** (see [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)) + **2026-08-27 V4 stable truth-sync** (see [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) + [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md))
**Documentation base (pre-V4-stable design docs):** 9900c10 (local ref only; pre-V4 beta worktree — **NOT** the V4 stable commit)
**V4 stable connector (durable binding):** `4ae5060931a64741185c5c8deb3886a5901f21cc` (short `4ae5060`, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`, Hermes Core MCP baseline `d7eba25ea8f6`)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [STALE_DOCS.md](STALE_DOCS.md) | [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) | [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md)

---

## 1. Evidence Hierarchy

Evidence is ranked as follows:

1. **Local source-bound investigations (primary):** t_2d568471 and its seven parents; completed 2026-08-19 without public research, repository writes, or live mutations.
2. **Corrected canonical task artifacts:** t_4d983898 (SoT/inventory), t_484d4ab0 (spec/ADR), t_4ce4ba8f (matrices/index), t_8a7b081c (roadmap/implementation/QA), t_1419658e (final 79-entry catalog).
3. **Operator-authoritative live discovery:** connector discovery on 2026-08-19 showing 54 exposed tools. This proves exposure only, never behavioral validation.
4. **Behavioral evidence:** actual invocation in the docs session or prior board QA. This is required for `AVAILABLE_VALIDATED`.
5. **Historical repository documents:** dated v0.1/v0.3/v0.4 contracts, deployment notes, reviews, and evidence. They remain useful within their date/scope but do not override newer source-bound findings without revalidation.

### Binding rules

- Current-state claims must include Hermes version and local documentation base; the **deployed connector SHA is now durably bound** to `4ae5060931a64741185c5c8deb3886a5901f21cc` (V4 stable, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`) — see [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) §0 and [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md). The prior `STILL_NOT_PROVEN` claim for the deployed connector SHA is **RESOLVED 2026-08-27**.
- `Kanban_Beta` is stale discovery metadata; controller evidence classifies deployment as STABLE. The **on-disk build.json `surface` value is now `beta`** for the V4 stable (controller still classifies as STABLE; no contract violation; documented residual).
- CLI/source is an oracle/contrast for dogfood; MCP calls are the subject under test.
- CLI registration or `--help` output is not behavioral PASS.
- Current scope vocabulary is exactly `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`; `offline_access` is connection-only. Finer scopes are PROPOSED only.
- Mutating dogfood uses disposable `hermes-chatgpt-e2e-*` fixtures only, never the project board `hermes-chatgpt-mcp`.

---

## 2. Remaining STILL_NOT_PROVEN Items

| Item | Why unresolved | Impact / next safe evidence |
|------|----------------|-----------------------------|
| ~~Exact deployed connector SHA~~ | **RESOLVED 2026-08-27** — was `STILL_NOT_PROVEN`; now durably bound to `4ae5060931a64741185c5c8deb3886a5901f21cc` (V4 stable, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`) | **REMOVED from `STILL_NOT_PROVEN`** — see [CHECKPOINT-2026-08-27-V4-STABLE.md §0](CHECKPOINT-2026-08-27-V4-STABLE.md) and [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md). Live readback (3 surfaces, all 4 headers match), 4 on-disk SHA-256 manifest pins matching R2, 8/8 prerequisites PASS. |
| ~~Live HTTP/API auth and reachability~~ | **PARTIALLY RESOLVED 2026-08-27** — public origin `https://kanban.hermesinthenight.duckdns.org` reachability proven for `/healthz`, `/mcp` (401 with bearer challenge), and OAuth discovery. Full native API surface (dashboard plugin mount, native Hermes REST, etc.) remains `STILL_NOT_PROVEN`. | **Reclassified as PARTIALLY_RESOLVED** — see [CHECKPOINT-2026-08-27-V4-STABLE.md §1a](CHECKPOINT-2026-08-27-V4-STABLE.md) for the live readback evidence. Native API surface still requires a fresh read-only discovery in a controlled environment. |
| Dashboard plugin live mount/auth | Source endpoints exist, but running gateway mount was not proven | Read-only plugin status/health evidence before workers/run MCP contracts |
| Provider/model validity and quota | Profile configuration and provider credentials were not exercised | Controlled non-mutating provider validation |
| Temporary per-task skill resolution | Partial source resolution depends on profile contents and dispatcher context | Disposable task preflight with no production mutation |
| Fine-grained profile permission enforcement | No Hermes-core enforcement path found; capabilities/refuses are advisory | Treat as advisory until explicit enforcement evidence exists |
| Managed overlay/effective controller config | Effective values known in places, complete overlay composition not pinned | Capture sanitized effective config in a controlled run |
| Live SQLite schema dump | Source schema inspected; live instance not dumped | Read-only schema introspection on disposable board |
| Native MCP/plugin/dynamic registration | Registry and static toolsets are inventoried; all runtime registration paths not proven | Read-only tool registry/runtime inventory |
| Skill metadata plugin integration | Local/builtin/hub origin semantics are known, plugin metadata source not fully proven | Read-only skill listing/view evidence |
| ChatGPT client `content_base64` support | Connector schema lacks remote field today; client ability to send future field is not proven | Contract/E2E test after schema extension |
| Current scopes for tools beyond explicit mappings | Catalog intentionally marks them `NOT_PROVEN / inherited policy` | Inspect live schema per tool; do not infer by operation type |

### Explicit current scope mappings

- `hermes:read`: all read-only tools (baseline).
- `hermes:create`: proven for `create_task` only.
- `hermes:manage`: proven for `add_comment` and `assign_task` only.
- `hermes:board:create`: proven for `create_board` only.
- `offline_access`: connection flow only; not a tool scope.

---

## 3. UNSAFE_TO_TEST Items

These remain unresolved by design because testing them against a live/protected control plane would mutate state or kill work:

| Item | Safety reason | Required test boundary |
|------|---------------|------------------------|
| Live `/kanban` connector delivery/ACL | Could exercise production write/auth paths | Disposable fixture + explicit auth test environment |
| Live terminate/reclaim/slash behavior | Can terminate or reclaim a worker/task | Disposable worker/run with guarded terminate contract |
| Live heartbeat/stale/crash/timeout behavior | Can alter liveness state and trigger reclamation | Disposable fixture with controlled clock/process |
| Raw terminal/process operations | Unrestricted process/shell behavior has no MCP-safe contract | Never expose through MCP |
| Destructive `gc`/`repair`/board deletion/workdir mutation | Data-integrity or filesystem mutation | Explicitly guarded admin environment; risk-based DO_NOT_EXPOSE |
| Secrets/auth/login/logout/update/uninstall operations | Credential/system state mutation | Never expose through MCP |

`UNSAFE_TO_TEST` is not the same as `NOT_PROVEN`: the former is a safety classification; the latter is an evidence gap.

---

## 4. Product and Surface Reconciliation

- **Live discovery:** 54 tools (18 read/introspection and 36 writes/actions).
- **Final catalog:** 79 entries, separating current exposure, current behavioral status, and planned V4 contract.
- **Native registry:** 87 unique leaf tools across 31 registry toolsets; not blanket operational availability.
- **Profiles:** 14 total; observed end-to-end spawn exactly `investigator`, `profile-architect`, `operator`, `software-architect`.
- **Skills:** 53 enabled semantics on default profile (39 builtin, 14 local, 0 hub); `sdlc-review` force-loaded for review dispatch.
- **CLI:** 74 top-level commands and 47 Kanban subcommands; no requirement to implement all 47 via MCP.
- **Specialized current gaps:** rich profiles/skills, validation, runtime info, `get_run`/`inspect_run`/`workers_active`/guarded terminate, remote base64 attachment, and general task edit.
- **Current `edit_task`:** completed-result edit only; full general task edit is planned V4.
- **Current `attach`:** local-path/server staging; remote `content_base64` planned V4. Hermes internal agent already supports `content_base64`.
- **Current `dispatch`:** exposed but manual call observed `BACKEND_ERROR`; classify `AVAILABLE_INCONSISTENT`.
- **Current `daemon`:** bounded MCP status/snapshot; standalone Hermes CLI daemon is deprecated.
- **Risk surfaces:** `gc`, `repair`, `boards-rm`, and workdir mutation are exposed but risk/admin/normal-use DO_NOT_EXPOSE candidates, not absent.
- **Pause/resume:** no board-local pause/resume; global ESTOP only.

---

## 5. Dogfood Incidents

1. **Post-complete artifact freeze (t_484d4ab0):** `kanban_complete` freezes durable result/artifacts; later workspace edits must not silently mutate completed artifacts. Corrections require explicit reissue/versioning.
2. **t_343 nonconvergence:** an earlier roadmap stream did not converge on the corrected scope/vocabulary; t_8a7b081c supersedes it.
3. **t_702 integration/stash incident:** the prior integration worker created a pre-safety stash. This task did not inspect, repair, drop, or mutate that stash or its non-authoritative worktree.
4. **Discovery vs stale checkout:** live discovery shows 54 tools while the documentation base checkout is older; discovery and local checkout must be reconciled explicitly.
5. **get_board capability inconsistency:** capability readback was inconsistent with successful writes; retain as a known issue until independently resolved.
7. **Manual dispatch `BACKEND_ERROR`:** current `dispatch` exposure exists, but a manual call returned `BACKEND_ERROR`; do not call it validated.
8. **DAG edge_state soft-retire (PROJECTION_RUNTIME_P0):** runtime `165d1849e25c` is edge_state-blind in `parent_ids`/`child_ids`/`task_graph_context`/`recompute_ready`/`_parents_satisfied`/`claim_task`/MCP fallback; `retired`/`rebound` edges still exert gating power. Canonical contract: [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md).
9. **Fixture leakage dogfood (PASS):** `t_a161305b`/run1114 and `t_85b5b14b`/run1118 created with `pid999999`/`boom`/`worker` on canonical board; reclaimed+archived canonically, no DELETE, review PASS. Root = `gave_up`+`promoted` without atomic run/claim closure + test isolation failure.

---

## 6. Stale-Claim Checks

The canonical set explicitly rejects these claims or scopes them correctly:

| Stale claim | Canonical treatment |
|-------------|---------------------|
| `9 live tools` | Replaced by 54-tool live discovery and 79-entry final catalog |
| `list_profiles` is CURRENT/live | It is a planned rich V4 contract; CLI evidence is not live MCP exposure |
| `board:read|board:write|board:admin` or `kanban:read|kanban:write|kanban:admin` are current | Replaced by current proven scope vocabulary; finer scopes are PROPOSED only |
| `implement all 47` | Explicitly rejected; inventory all 47, expose only approved MCP contracts |
| `hermes kanban inspect` is required/current | Explicitly rejected; use dashboard/source primitive for V4 `inspect_run` |
| Mutating dogfood against `hermes-chatgpt-mcp` | Explicitly prohibited; use disposable `hermes-chatgpt-e2e-*` fixtures |
| `--help` proves behavioral validation | Explicitly rejected; registration ≠ behavioral PASS |
| Agent must be changed to send base64 | Incorrect; Hermes internal agent already supports `content_base64`; MCP transport is missing it |
| Deployed SHA is known from local ref or `Kanban_Beta` | Explicitly rejected; deployed connector SHA is STILL_NOT_PROVEN |

---

## 7. Source and Historical References

- Canonical source task: t_4d983898 (`SOURCE-OF-TRUTH-DRAFT.md`)
- Stale inventory source: t_4d983898 (`STALE-DOCS-INVENTORY.md`)
- Corrected spec/ADR: t_484d4ab0
- Matrices/index: t_4ce4ba8f
- Roadmap/implementation/QA: t_8a7b081c
- Final catalog: t_1419658e
- Synthesis/local evidence: t_2d568471 and parents
- Historical repository docs: [STALE_DOCS.md](STALE_DOCS.md)

---

## 8. 2026-08-21 Release-Candidate Decision Trail & Supersession (truth-sync — supplemental)

This section records the live release-candidate decision trail and supersession links so older cards are not mistaken as current authority. The canonical design evidence above (sections 1–7, dated 2026-08-19) remains authoritative for architecture/scope. Full reconciliation in [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md).

### Decision trail
- **`t_72108336` (V4-GAP-TRIAGE, done) + human decision in comment 579:** Do **NOT** convert all G1–G20 into Phase-S/beta blockers. G1 is the only substantive new platform correction blocking immediate Phase-S; minimal fresh-session/provenance test-integrity is required; remaining gaps belong to existing V4 waves, dogfood, or other boards.
- **Outcome-gate recovery:** `t_b0901b4a` blocked/gave-up (partial, useful) → `t_c4c38028` (freeze candidate, running) → `t_09f51d5a` (adversarial/race, todo) → `t_8c125abe` (reactivate review, todo) → `t_fc541b39` (independent ACCEPT, blocked) → `t_7c2f0fdd` (real-board dogfood, todo). Gate closeout **NOT_PROVEN** until `t_fc541b39` ACCEPT + `t_7c2f0fdd` proof.
- **Provenance:** `t_415df0f5` PASS (independent review); `t_dadd5ebf` fresh provenance **GO** — evidence only, **NOT release/build/deploy authorization**.
- **Canary:** `t_be036abf` requires fresh MCP/OAuth session + observed receipt before first mutation; mismatch/unknown identity ⇒ FAIL (§6 of checkpoint).

### Supersession notes
- **`t_e1b6bae8`** (S-UNBLOCK-CHAIN) — HISTORICAL / SUPERSEDED for the current release chain (tied to older recovery preconditions). Not deleted; `t_e187bee7` is the current hold-rebind authority.
- **Old "Release triage note" (TBD)** on `my-hermes-config` PR #49 — superseded by the 2026-08-21 decision trail above and by `t_72108336` comment 579. (Orchestration-scope report `t_b67c9ab8`; do not duplicate the full connector roadmap there.)
- **`t_b0901b4a`** — partial/gave-up with successor chain; never read as a completed gate.
- **Canonical 2026-08-19 docs** — authoritative for design/scope; where they conflict on *release-candidate* status, Kanban (live) wins and the doc should be re-reconciled.

### Evidence-state summary (point-in-time)
- **Deployed connector SHA: RESOLVED 2026-08-27** — bound to `4ae5060931a64741185c5c8deb3886a5901f21cc` (V4 stable, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`). See [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) and [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md).
- Outcome-gate closeout: **NOT_PROVEN** (pending `t_fc541b39` + `t_7c2f0dd`) — unchanged from 2026-08-21; the V4 stable cutover is **independent** of the outcome-gate closeout (the DAG soft-retire contract [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md) is the contract; the `4ae5060` runtime is **edge_state-aware**, so the `PROJECTION_RUNTIME_P0` blocker is closed; the outcome-gate closeout is the next milestone, not a V4 stable prerequisite).
- G1: **closed in `4ae5060`** (connector-side; outcome-gate chain still pending as a separate concern).
- Release authorization: **RECEIVED 2026-08-27** via parent `t_1e84eb11` ACCEPT (all 8 prerequisites PASS, all Human Gates YES on exact `4ae5060`).
- All canonical UNSAFE_TO_TEST items remain unresolved by safety classification.
- V4 stable residuals (F-DOGFOOD-01, W0 Low init, ephemeral worker venv, `deployed_at` semantics, no stable checkout dir, 8791 dormant) are documented and non-blocking — see [CHECKPOINT-2026-08-27-V4-STABLE.md §6](CHECKPOINT-2026-08-27-V4-STABLE.md).

---

## 9. 2026-08-27 V4 Stable Truth-Sync — Residual Register (supplemental)

This section records the **known residuals** explicitly preserved by the V4 stable acceptance. These are not blockers; they are accepted as documented limitations of the current V4 stable cutover and are durable evidence in the V4 stable release provenance.

| # | Residual | Severity | Source | Why retained |
|---|----------|----------|--------|---------------|
| 1 | **F-DOGFOOD-01** `bounded_log` cursor `BACKEND_ERROR` — additive convenience only; `tail_bytes`, `get_activity`, `runtime_status`, `diagnostics` cover the observability acceptance | LOW, fail-closed | `t_45647dc7` extended dogfood (88/1) | Fix would require a new connector release + its own E2E + dogfood chain; out of scope for V4 stable cutover |
| 2 | **W0 Low** `initialize` 1999-01-01 negotiates 2025-11-25 — no security impact | LOW | `t_068740be` independent review | Historical carry; no functional or security impact; deferred to a future wave |
| 3 | **Ephemeral worker venv** `hermes_cli` `ModuleNotFoundError` — isolated to canary venv, bounded non-leak, not reproduced in retest, does not affect stable 8789 | LOW | canary-side observation | Bounded to canary venv; stable 8789 unaffected |
| 4 | **`deployed_at` semantics** — `build.json` reports `2026-08-26T14:34:00Z` which is the canary's original deploy time, not the 2026-08-27 R2 cutover time | Informational | `t_a47fd88f` POST_SWITCH_REPORT residual note | No contract violation; downstream consumers reading `deployed_at` may interpret it as "stable cutover time" — documented for clarity |
| 5 | **No `/opt/hermes-chatgpt-mcp` (stable checkout dir)** — stable venv exists at `/opt/venvs/hermes-chatgpt-mcp`; the corresponding checkout dir does not exist on this host; rollback uses the venv only | Informational | `t_1e84eb11` parent handoff | Rollback path documented; no checkout needed |
| 6 | **Pre-V4 `hermes-chatgpt-mcp-beta.service` (8791) not running** in the V4 stable topology; pre-V4 `8791` deployment unit and `/var/lib/hermes-chatgpt-mcp-beta` state dir still exist on disk | Informational | live readback (no process on 8791) | Resurrecting 8791 requires fresh authorization; out of scope for V4 stable cutover |

See [CHECKPOINT-2026-08-27-V4-STABLE.md §6](CHECKPOINT-2026-08-27-V4-STABLE.md) for the full residual register, including the F-DOGFOOD-01 chain (DIAGNOSE→FIX→REVIEW→REGRESSION→RETEST) and how each residual is bounded.
