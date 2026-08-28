# V4 Current-Truth Freshness Checkpoint — 2026-08-25

**Status:** DOCUMENTATION TRUTH-SYNC (supplemental to the canonical 2026-08-19 V4 design docs + 2026-08-21 and 2026-08-24 reconciliations)
**Reconciliation date:** 2026-08-25 (UTC)
**Authored by:** github-steward (task `t_6e482547`); **Augmented by:** github-steward (task `t_ed19e80c`) with DAG soft-retire contract cross-reference.
**Documentation base:** `9900c10` (local ref only; deployed connector SHA is **NOT_PROVEN** — carried from canonical docs)
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

### 3a. `hermes-chatgpt-mcp` (this repo — V4 control plane / MCP connector)

| Item | Value | Evidence / source |
|------|-------|-------------------|
| Public MCP E2E runtime fix | `dc25e8bf7a66be87e12da33613d83c874be50038` | commit in this repo; `mcp-public-e2e-postrestart-20260824.md` |
| Live tool surface | **54 tools** enumerated via `tools/list` | public E2E 2026-08-24 (disposable board `gate-test-2310970`, task `t_fdd65121`) |
| `create_task` write/readback | **PASS** (OAuth register/authorize/token → MCP init → `tools/list` 54 → `create_task(arguments.request)` → `get_task` readback) | same E2E report |
| Deployed connector SHA | **STILL_NOT_PROVEN** | carried canonical finding; pin at clean-build identity |
| Canonical docs branch | `docs/v4-control-plane-source-of-truth-final` @ `ea72236` (this checkpoint's base) | PR #2 (open, base `beta/board-management`) |

> **Qualification required:** Older repo docs describing the surface as *seven READ + one WRITE*, *eight tools*, or *eleven tools* (see §5 stale markers) are **historical v0.x contracts** and MUST NOT be presented as current runtime truth without explicit qualification. The current live surface is 54 tools.

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
