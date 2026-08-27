# V4 Current-Truth Freshness Checkpoint — 2026-08-25

**Status:** DOCUMENTATION TRUTH-SYNC (supplemental to the canonical 2026-08-19 V4 design docs + 2026-08-21, 2026-08-24, **2026-08-25 DAG soft-retire contract**, and **2026-08-27 V4 stable truth-sync** reconciliations). This document is the **Source Precedence Ladder + cold-start protocol**; it is unchanged as a methodology document by the 2026-08-27 V4 stable acceptance. The 2026-08-27 V4 stable truth-sync lives in [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) + [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md); the V4 stable is **durable binding** at `4ae5060931a64741185c5c8deb3886a5901f21cc` (branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`).
**Reconciliation date:** 2026-08-25 (UTC); **V4 stable binding 2026-08-27** (carried)
**Authored by:** github-steward (task `t_6e482547`); **Augmented by:** github-steward (task `t_ed19e80c`) with DAG soft-retire contract cross-reference.
**Documentation base:** `9900c10` (local ref only; pre-V4 beta worktree — **NOT** the V4 stable commit) **+ V4 stable binding 2026-08-27**
**Companion review card:** `t_d83ac017` (independent truth-sync audit for this checkpoint)
**Scope of this document:** Fix the documentation defect exposed by the Command Code cold-start test — repo docs and historical cards were allowed to outrank live Kanban/runtime truth. This is a documentation/system-design change only. No Git changes to any live runtime repo, no service/restart/deploy/OAuth/DCR/V4/downstream mutation.

---

## 0. How to determine current truth — Source Precedence Ladder

When answering "where are we now?", rank sources from highest authority to lowest. A lower-ranked source **never** overrides a higher-ranked one. When they conflict, mark the lower one **STALE** before citing it as current.

| Rank | Source | Notes |
|------|--------|-------|
| 1 | **Live runtime / service readback** | Live MCP discovery, `/healthz` build identity, authenticated read probes, public E2E — captured **at execution time** |
| 2 | **Live canonical Kanban state** | Current tasks / runs / events on board `hermes-chatgpt-mcp` (cross-board items noted per card) |
| 3 | **Fresh immutable evidence bound to exact SHA / run id** | Build & provenance receipts, E2E reports, manifest hashes — only if the SHA/run is the thing under question |
| 4 | **Current Git HEAD / worktrees / refs** | Per exact commit; the checked-out doc tree is **not** automatically truth |
| 5 | **Current checkpoints / manifests** | Dated point-in-time snapshots (this `docs/v4` set) |
| 6 | **Current repo docs** | This `docs/v4` set at its documented base |
| 7 | **Historical terminal cards** | Dated Kanban tasks; superseded ancestors are explicitly NOT current authority |
| 8 | **Archived / superseded cards** | Retained for history only |
| 9 | **Old docs** | v0.1 / v0.3 / v0.4, pre-V4 design/plans |
| 10 | **Project / harness memory** | Agent/durable memory; useful but never authoritative for current state |
| 11 | **Inference** | Model guesswork — lowest; never authoritative |

> A doc or card's *age* does not make it wrong within its own scope, but it does not get to outrank a live readback. **Discovery ≠ validation**, and **a stale checkout is not the runtime.**

---

## 1. Cold-start / current-state recovery protocol

When asked "where are we now?" — before answering from memory or history:

1. **Refresh the board:** read current RUNNING / READY / P0 items on Kanban (board `hermes-chatgpt-mcp`).
2. **Resolve latest generation of each chain:** pick the newest card in a chain, not a superseded ancestor (e.g. do not cite `t_e1b6bae8` for the current hold-rebind authority — `t_e187bee7` is current).
3. **Inspect current Git HEAD / worktrees / refs** to the exact commit.
4. **Resolve the exact current candidate / review / gate** per owning repo (these are distinct across `hermes-chatgpt-mcp` and `hermes-agent`).
5. **Re-run runtime / public E2E readback** (live 54-tool surface, `create_task` write/readback). **Do not quote an old tool count** (8 / 11 / 7+1) as the current runtime.
6. **Only then assemble the answer.** Mark any doc or card that contradicts live state as **STALE** before using history.

**Live-drift / recovery gate state MUST be read live at execution time and stamped with the read timestamp.** Never copy it blind from an older card.

---

## 2. Project Model (persistent) vs Current State Vector (volatile)

Keep these two layers distinct in every "current state" answer.

**Project Model (persistent — rarely changes):**
- Architecture, topology, ADRs
- Principles, scope, declared roadmap
- History (incidents, terminal verdicts, decision trails)
- Dogfood program record

**Current State Vector (volatile — re-derived live each time):**
- Current Git HEAD / exact candidate SHA
- Latest accepted / in-review review
- Active gate and its status
- RUNNING / READY / P0 board state
- Freeze / drift / recovery state (with read timestamp)
- Blockers and next join

The Project Model answers "what is the system designed to be"; the Current State Vector answers "what is true right now". A checkpoint is a dated snapshot of the Vector, never a replacement for a live read.

---

## 3. Current State Vector snapshot — 2026-08-25 (read live before acting)

> All items below are **evidence as of 2026-08-25, UTC**. Re-derive from the cited source before any decision. SHAs attributed to their **owning repo**; do not conflate `hermes-chatgpt-mcp` with `hermes-agent`.

### 3a. `hermes-chatgpt-mcp` (this repo — V4 control plane / MCP connector) — 2026-08-25 snapshot

| Item | Value | Evidence / source |
|------|-------|-------------------|
| Public MCP E2E runtime fix | `dc25e8bf7a66be87e12da33613d83c874be50038` | commit in this repo; `mcp-public-e2e-postrestart-20260824.md` |
| Live tool surface | **54 tools** enumerated via `tools/list` | public E2E 2026-08-24 (disposable board `gate-test-2310970`, task `t_fdd65121`) |
| `create_task` write/readback | **PASS** (OAuth register/authorize/token → MCP init → `tools/list` 54 → `create_task(arguments.request)` → `get_task` readback) | same E2E report |
| Deployed connector SHA | **STILL_NOT_PROVEN** (at this checkpoint's date) | carried canonical finding; pin at clean-build identity |
| Canonical docs branch | `docs/v4-control-plane-source-of-truth-final` @ `ea72236` (this checkpoint's base) | PR #2 (open, base `beta/board-management`) |

> **Qualification required:** Older repo docs describing the surface as *seven READ + one WRITE*, *eight tools*, or *eleven tools* (see §5 stale markers) are **historical v0.x contracts** and MUST NOT be presented as current runtime truth without explicit qualification. The current live surface is 54 tools.

### 3a'. `hermes-chatgpt-mcp` — 2026-08-27 V4 stable binding (supersedes §3a for current-state authority)

| Item | Value | Evidence / source |
|------|-------|-------------------|
| V4 stable connector SHA | `4ae5060931a64741185c5c8deb3886a5901f21cc` (branch `v4-candidate-integration`) | live readback (3 surfaces, all 4 headers match); 4 on-disk SHA-256 manifest pins matching R2; 8/8 prerequisites PASS |
| Live tool surface | **71 tools** enumerated via `tools/list` | post-switch smoke `t_a47fd88f` contract check #10 (vs the 2026-08-25 54-tool snapshot) |
| v4.wave0 required tools (all 6 present) | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` | `t_a47fd88f` contract check #10 |
| Surface | `beta` (controller classifies as STABLE; `Kanban_Beta` discovery label is stale naming metadata) | build.json `surface` + response header `x-v4-provenance` |
| API surface version | `v4.wave0` | response header `x-api-version` |
| Hermes Core MCP baseline | `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` (header short `d7eba25ea8f6`; branch `v4/baseline-post-update-885e9ef`) | response header `x-baseline-mcp` + `x-baseline-branch` |
| Phase-S source bundle | `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` (branch `release/source-bundle-phase-s`) | `v4-candidate-integration` branch history |
| V4 stable canonical docs branch | `docs/v4-control-plane-source-of-truth-final` @ `76cde68cba05` (this truth-sync's base) | PR #2 (open, base `beta/board-management`); truth-sync PR proposed via `docs/v4-post-v4-stable-truth-sync` |
| Pre-promotion backups (rollback targets) | `build.json.pre-surface-rectification-20260826T103951Z.bak` (`d7eba25ea8f6`, surface=`stable`, deployed_at=`2026-08-25T15:13:56Z`); `build.json.pre-edge-state-20260825T1440Z.bak` (`dc25e8bf7a66…`, surface=`stable`, deployed_at=`2026-08-24T19:35:56Z`) | on-disk in `/var/lib/hermes-chatgpt-mcp/` |

> **Authority:** §3a is the 2026-08-25 snapshot (the date of this checkpoint). §3a' is the 2026-08-27 V4 stable binding. **§3a' is authoritative for the current V4 stable runtime**; §3a remains as the historical 2026-08-25 snapshot for the live-drift / cold-start protocol methodology. The full evidence chain is in [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) + [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md).

### 3b. `hermes-agent` (sibling repo — governance-port recovery candidate)

These SHAs are **not** in `hermes-chatgpt-mcp`. They are an isolated, reviewed-but-not-integrated candidate in the `hermes-agent` fork.

| Item | Value | Evidence / source |
|------|-------|-------------------|
| Governance-port base (exact, = live `hermes-agent` main at port time) | `ab0d9841450b0ead5e3d3116fbd1f1e1dfb7c462` | `t_e0afe121` / `governance-port-ab0d-verification-summary.md` |
| Reviewed candidate head | `011c7e9805d577aaae67f7e22f6fba79fa65657e` (11 commits over base) | same; pushed as new branch `recovery/governance-port-ab0d-20260825` to `arumihsnek/hermes-agent` |
| Port task | `t_e0afe121` — **DONE** (outcome CANDIDATE_READY_FOR_REVIEW) | live Kanban, status `done` (verified 2026-08-25) |
| Independent review | `t_f5a59327` — **DONE** (verdict PASS, run 1098) | live Kanban, status `done` (verified 2026-08-25) |
| External manifest SHA256 | `3e97709b70cd40d94d57e9bae5ddacc975614c2322701b47f76734c8018bb9fe` | manifest self-verifies `ok:true` via `verify_recovery_governance_manifest.py --expected-head` |

> **State:** candidate is in-review / eligible only for a later candidate-bound Human Gate. **Zero integration / deploy authority.** Live `hermes-agent` main remains `ab0d984…` (proven unmutated). Read the live gate state before treating this as current.

### 3c. Live-drift / recovery gate

The 2026-08-24 recovery gate state is documented in `RECOVERY-TRUTH-SYNC-2026-08-24.md` and the 2026-08-25 governance-port summary. **These are point-in-time.** The live drift/recovery gate state must be re-read live at execution time with a timestamp; do not copy from this or any older card.

---

## 4. Dogfood finding — cold-start source-precedence mis-rank

**Finding (from the Command Code cold-start test):** Cold-start context recovery achieved high *historical coverage* — architecture, history, and decision trails were recovered well — but **mis-ranked freshness / source precedence**: repo docs and historical cards were permitted to outrank live Kanban and runtime readback when answering "where are we now?".

**Classification:** This is a **documentation / system-design defect**, not solely a model-error incident. The recovery harness lacked an explicit, enforced precedence ladder and a cold-start current-state protocol; the model faithfully reproduced the highest-coverage material (history) instead of the highest-authority material (live state).

**Required structural fix (this checkpoint):** the Source Precedence Ladder (§0) and Cold-start Protocol (§1) make the ranking machine/actionable and stale-resistant, so future cold starts refresh live state before citing history.

**Preserved history:** the underlying incidents/verdicts referenced here are retained verbatim and dated; only their *precedence* is corrected. No old terminal verdict is rewritten.

---

## 5. Stale markers applied by this checkpoint

Docs now required to carry a **STALE / REVALIDATE** flag for current-runtime claims (qualification required before presenting as current):

| Doc | Stale boundary | Required qualifier |
|-----|---------------|--------------------|
| `README.md` (root) | "seven READ tools plus one WRITE" — v0.4 surface | Label as v0.4; current live MCP surface is 54 tools |
| `docs/SECURITY.md` | "eight-tool allowlist" (v0.4) | v0.4 security contract; V4 inventory is 54 tools |
| `docs/DEPLOYMENT.md` | "beta exposes eleven tools" | Dated v0.x; not current runtime count |
| `docs/architecture/HERMES-INTEGRATION.md` | "eleven tools total" | Dated 2026-08-16, v0.4; superseded by 54-tool discovery |
| `docs/evidence/BETA-BOARD-MANAGEMENT-PLAN-2026-08-16.md` | "eleven tools" beta plan | Dated plan; retained as history |
| `docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp-beta.md` | "eight tools stable / eleven beta" | Dated plan; history only |

These remain **RETAIN / LINK** as dated v0.x contracts (per `STALE_DOCS.md`); they are flagged here only so they cannot masquerade as current runtime truth.

---

## 6. Next semantic checkpoints (not yet passed)

1. Independent truth-sync audit of this checkpoint — `t_d83ac017`.
2. Any downstream acceptance/release gate remains **NOT_GRANTED**; no document here authorizes build/deploy/release.
3. **DAG soft-retire contract (2026-08-25, `t_ed19e80c`):** canonical `task_links.edge_state` soft-retire + PROJECTION_RUNTIME_P0 release blocker recorded at [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md). This is documentation truth only; it does not authorize runtime mutation.

---

*Reconciliation performed by github-steward under task `t_6e482547`. Re-derive live status from Kanban and live readback before any decision; this checkpoint is a point-in-time truth-sync, not live state. SHAs are attributed to their owning repo (`hermes-chatgpt-mcp` vs `hermes-agent`); do not conflate.*
