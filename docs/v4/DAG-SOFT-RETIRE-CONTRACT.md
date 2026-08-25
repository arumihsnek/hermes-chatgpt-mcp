# DAG / Projection Soft-Retire Contract & Release Blocker — Canonical Truth

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE (supplemental)
**Authored by:** github-steward (task `t_ed19e80c`)
**Reconciliation date:** 2026-08-25 (UTC)
**Documentation base:** `9900c10` (local ref only; deployed connector SHA is **NOT_PROVEN** — carried from canonical docs)
**Companion card:** `t_31d1c67f` (implementation), `t_20dd938c` (review), `t_ef3ae8d4` (activation-gate-prep)
**Scope:** Documentation-only truth persistence. No Git mutation to any live runtime repo, no service/restart/deploy/OAuth/DCR/V4/downstream mutation, no `DELETE` of retired edges, no `barrier` completion for throughput.

---

## 0. Update precedence

This document is **current repo docs** (rank 6 on the Source Precedence Ladder in [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)). It is superseded by live runtime readback, live Kanban state, and SHA-bound evidence if any of those contradict it. Every claim here is evidence-bound and dated; re-derive live state before any decision.

---

## 1. Canonical DB soft-retire contract — `task_links.edge_state`

The DAG edge table `task_links` gains a lifecycle column and provenance columns. This section is the **canonical contract** for the migration; it is documented truth, not yet deployed (see §2).

### 1a. Lifecycle states

`task_links.edge_state ∈ { active | retired | rebound }`

| State | Meaning | Gating power |
|-------|---------|--------------|
| `active` | Current, participating edge | Full gating power in every boundary (reader, evaluator, graph, dispatch, promotion, claim) |
| `retired` | Soft-removed edge; replaced/replaced-by provenance recorded | **Zero gating power** — MUST be ignored by every gating boundary |
| `rebound` | Previously retired edge that has been re-activated (re-bound) | **Zero gating power while in `rebound`** until an explicit re-activation step promotes it to `active`; a `rebound` edge never silently regains gating power |

**Invariant:** `retired` and `rebound` edges carry **zero gating power**. No reader, evaluator, graph builder, dispatcher, promoter, or claimer may treat a non-`active` edge as a blocking dependency.

### 1b. Replacement provenance fields (historical evidence only)

These columns are **historical evidence**, never gating inputs:

- `replaced_by_parent_id` — the parent edge that supersedes this one.
- `recovery_relation_id` — the recovery/rebind relation that produced this row.
- `retired_at` — timestamp the edge was soft-retired.
- `retired_by` — actor/id that performed the soft-retire.

An evaluator MUST NOT use `replaced_by_parent_id` / `recovery_relation_id` / `retired_at` / `retired_by` to reconstruct or infer a dependency. They are an audit trail, not a gating graph.

### 1c. Soft-retire, never hard-delete

Retirement is a **state transition** (`active → retired`), not a row deletion. The deployment invariant (§2) forbids deleting retired-edge rows for throughput or cleanup. Historical edges remain inspectable and reconstructable from provenance.

---

## 2. Deployment invariant (migration gate)

The schema/provenance migration is **NOT deployed** until **every** consumer boundary uses the new semantics:

1. **reader** — `parent_ids` / `child_ids` must exclude non-`active` edges.
2. **evaluator** — dependency satisfaction must ignore `retired` / `rebound`.
3. **graph** — `task_graph_context` / graph builder must not surface non-`active` edges as live edges.
4. **dispatch** — dispatch eligibility must not block on non-`active` edges.
5. **promotion** — `promote_tasks` must not require non-`active` edge closure.
6. **claim** — `claim_task` / `_parents_satisfied` / `recompute_ready` must treat non-`active` edges as satisfied/absent.

Until all six boundaries are proven edge-aware, the migration is **NOT_PROVEN deployed** and the runtime remains edge_state-blind (see §3).

---

## 3. Exact incident evidence — PROJECTION_RUNTIME_P0

**Classification:** `PROJECTION_RUNTIME_P0` (projection/runtime defect, not a DB-schema defect — the schema contract is correct; the runtime does not read it).

### 3a. What was proven correct

- `run1138` / `run1139` rebind were **correct** (rebind intent and data applied as designed).
- `active-dead-parent` count = **0** (no active edge points at a dead/deleted parent).
- `PRAGMA` integrity check **ok** (SQLite schema/integrity healthy).

### 3b. The defect

The Hermes runtime pinned at commit **`165d1849e25c7653a4c1879ca8410475eb8a7d52`** is **edge_state-blind** in:

- `parent_ids` — returns edges regardless of `edge_state`.
- `child_ids` — returns edges regardless of `edge_state`.
- `task_graph_context` — builds graph including non-`active` edges.
- `recompute_ready` — recomputation gating ignores `edge_state`.
- `_parents_satisfied` — parent-satisfaction ignores `edge_state`.
- `claim_task` — claim gating ignores `edge_state`.
- **MCP fallback** — the connector fallback path also ignores `edge_state`.

Because the runtime reads `active` and `retired`/`rebound` edges identically, a soft-retired edge still exerts gating power — violating the §1 invariant. This is a **runtime/reader bug**, fixable without schema change, but it blocks the §2 migration gate until all six boundaries are made edge-aware.

### 3c. Disposition

- Schema contract (§1) remains canonical and unchanged.
- Runtime fix (make the six boundaries edge-aware) is the implementation lane: `t_31d1c67f`.
- No deletion of retired edges is permitted to "fix" this (would destroy provenance and violate §1c).

---

## 4. Fixture leakage dogfood — canonical reclaim (no DELETE)

**Finding:** Fixture leakage occurred when dogfood tasks created artifacts against the **canonical board** instead of a disposable `hermes-chatgpt-e2e-*` fixture.

| Task | Run | Leak artifact | Disposition |
|------|-----|---------------|-------------|
| `t_a161305b` | run1114 | created with `pid999999` / `boom` / `worker` against canonical board | reclaimed + archived canonically, **no DELETE** |
| `t_85b5b14b` | run1118 | created with `pid999999` / `boom` / `worker` against canonical board | reclaimed + archived canonically, **no DELETE** |

**Review:** PASS. Both were reclaimed (returned to a terminal/reclaimable state) and archived through canonical board operations. **No hard `DELETE`** of board/task rows was performed — consistent with the soft-retire philosophy (§1c) and the dogfood rule that mutating dogfood must stay on disposable fixtures.

**Root pattern:** `gave_up` + `promoted` WITHOUT atomic run/claim closure, plus a **test isolation failure** (the fixture was not isolated to a disposable board). The fix is (a) enforce atomic run/claim closure before promote, and (b) enforce fixture-board isolation in the dogfood harness.

---

## 5. Current truth — lanes and gates (read live before acting)

> Re-derive from Kanban at execution time; below is the 2026-08-25 snapshot.

| Item | State | Evidence |
|------|-------|----------|
| `t_31d1c67f` | **implementation lane** (edge-aware runtime fix) | live Kanban |
| `t_20dd938c` | **review** | live Kanban |
| `t_ef3ae8d4` | **activation-gate-prep** | live Kanban |
| `barrier` | **closed** | live Kanban |
| `V4` (V4-CUT3) | **closed** | live Kanban |

---

## 6. Release path (ordered, fail-closed)

The release must NOT delete retired edges or complete `barrier` for throughput. Exact order:

1. **Deploy edge-aware runtime** under a **fresh Human Gate**, with **live readback** proving all six boundaries (§2) ignore non-`active` edges. Do not promote without readback.
2. **Fresh upstream acceptance** — if the contract requires replacing the historical acceptance card `t_47fcecec`, perform a fresh upstream acceptance run bound to the new edge-aware runtime. The historical card is **not** current authority.
3. **Open `barrier`** only after (1) and (2) are proven.
4. **V4-CUT3** only after `barrier` is open and the §2 migration gate is fully satisfied.

Deviations (e.g. deleting retired edges, completing `barrier` early) are **prohibited** by this contract.

---

## 7. Durable ledger entries

### 7a. Dogfood / gaps ledger

- **DOGFOOD-LEAK-FIXTURE-BOARD:** `t_a161305b`/run1114 and `t_85b5b14b`/run1118 leaked onto canonical board with `pid999999`/`boom`/`worker`; reclaimed+archived canonically, no DELETE, review PASS. Root = `gave_up`+`promoted` without atomic run/claim closure + test isolation failure.
- **GAP-RUNTIME-EDGE_STATE-BLIND:** runtime `165d1849e25c` is edge_state-blind in `parent_ids`/`child_ids`/`task_graph_context`/`recompute_ready`/`_parents_satisfied`/`claim_task`/MCP fallback → `PROJECTION_RUNTIME_P0`.
- **GAP-MIGRATION-GATE:** schema/provenance migration NOT deployed until reader/evaluator/graph/dispatch/promotion/claim are all edge-aware.

### 7b. Stale-semantics markers (explicit)

- Any doc or runtime path that treats `retired`/`rebound` edges as gating is **STALE** and must be corrected to §1.
- Historical acceptance card `t_47fcecec` is **HISTORICAL/SUPERSEDED** for current acceptance; a fresh upstream acceptance replaces it only if the contract requires (§6.2).

---

## 8. Cross-references

- Source Precedence Ladder / cold-start: [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)
- Release-candidate decision trail: [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) §8
- Current state vector: [CURRENT_STATE.md](CURRENT_STATE.md) §15
- Roadmap / gates: [ROADMAP.md](ROADMAP.md)
- Stale-doc handling: [STALE_DOCS.md](STALE_DOCS.md)

---

*Reconciliation performed by github-steward under task `t_ed19e80c`. Re-derive live status from Kanban and live readback before any decision; this is a point-in-time truth-sync, not live state. SHAs are attributed to their owning repo; do not conflate `hermes-chatgpt-mcp` with `hermes-agent`.*
