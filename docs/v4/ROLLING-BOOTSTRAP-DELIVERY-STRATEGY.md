# V4 Rolling / Self-Hosting Bootstrap — Canonical Delivery Strategy

**Status:** CANONICAL V4 DELIVERY STRATEGY (supplemental to the canonical V4 design docs)
**Authored by:** github-steward (task `t_4b01a9b7`)
**Reconciliation date:** 2026-08-25 (UTC)
**Documentation base:** `9900c10` (local ref only; deployed connector SHA is **NOT_PROVEN** — carried from canonical docs)
**Companion critical-path preflight:** `t_4b49ff1e` (`V4-RELEASE-CRITICAL-PATH-PREFLIGHT.md`)
**Scope:** Documentation-only strategy adoption. This card does NOT start V4 implementation, does NOT touch any live runtime/service/OAuth/barrier/CUT3/V4 board, and does NOT mutate `docs/v4-control-plane-source-of-truth-final` directly (it lands via an independent-review PR — see §7).

---

## 0. Update precedence

This document is **current repo docs** (rank 6 on the Source Precedence Ladder in [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)). It is superseded by live runtime readback, live Kanban state, and SHA-bound evidence if any of those contradict it. Re-derive live state before any decision; every claim here is evidence-bound and dated.

---

## 1. Decision — rolling/self-hosting bootstrap is NOW the canonical delivery strategy

Adopt self-hosting **rolling V4** as the canonical delivery strategy for V4, effective immediately and **before V4-CUT3**. This replaces the prior implicit **big-bang** posture (deliver the whole V4 at once behind a single CUT3) with a **progressively promoted, self-accelerating lane** of durable tranches.

This is a *delivery-strategy* change only. It does **not**:
- change the canonical V4 architecture, scope, or P0/P1/P2/P3 feature set (those remain owned by [ROADMAP.md](ROADMAP.md) + [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md));
- start any V4 implementation work (that still awaits `t_765c4305` / CUT3 and the prerequisite chain in §5);
- weaken or bypass the final integrated candidate / canary / E2E / dogfood / Human Gate / stable ACCEPT gates (§6).

Rolling delivery means: each tranche is independently implementable, testable, reviewable, and **dogfoodable in isolation** once it satisfies its own gates — long before the full V4 is assembled.

---

## 2. Invariants — protected state and hard rules

### 2.1 `stable-current` remains protected
- The currently-shipped connector/service (classified STABLE; the `Kanban_Beta` discovery label is stale metadata) is **never** the target of a rolling tranche.
- No rolling tranche is promoted to `stable-current` directly. Promotion flows exclusively through the final integrated candidate path (§6).
- A reviewed, dogfooded tranche lives in a **separate, progressively promoted lane** (a candidate/beta surface or a feature-pinned branch), demonstrably isolated from `stable-current` until the integrated gate.

### 2.2 No direct commit-to-stable
- A rolling tranche never commits its enabling change to the stable/mainline delivery path. It lands first on its own candidate lane, accumulates review + dogfood evidence, and is eligible for `stable-current` **only** via the integrated promotion gate (§6.4).
- This is the same fail-closed discipline already enforced for the DAG soft-retire contract ([DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)): no `barrier` completion, no `stable` jump, no CUT3 for throughput.

### 2.3 Every rolling tranche has exact candidate / rollback / acceptance
Each tranche definition MUST pin, before any dogfood:
- **candidate**: the exact branch/commit/SHA or deployed surface the tranche is exercised against (SHA-bound, never "latest").
- **rollback**: the exact prior-good state to revert to if the tranche's acceptance fails or regression is proven (one-step, demonstrable, no data-loss).
- **acceptance**: the explicit, observable acceptance criteria (tests + independent review + bounded activation result) that must all PASS before the tranche is declared dogfood-ready in its lane.

### 2.4 No big-bang wait
- A tranche may be dogfooded **after its own** implement + tests + independent review + bounded activation — *without* waiting for all W0–W4 (the old big-bang wave set) to complete.
- Dogfood of a reviewed bootstrap capability is explicitly permitted and encouraged; it is bounded to its own candidate lane and its own rollback.

### 2.5 Self-acceleration priority
- Tranche ordering is driven by **self-acceleration value**: first ship the capabilities that make *later* V4 safer and faster to build, test, and verify.
- This is why bootstrap/runtime/contract capabilities (B0) precede feature breadth (B4).

---

## 3. Tranche ordering (intent) — B0 → B4

Ordering is *intent*, not a hard gate on later tranches: a later tranche may still be spec'd in parallel, but promotion priority follows self-acceleration value.

### B0 — Task/DAG/runtime contract + generation rollover + scheduler/wake/authority/isolation/recovery
Foundational. Makes every later tranche safer to build and verify:
- Task + DAG contract (including the edge_state soft-retire contract — [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)).
- Generation rollover (fresh-generation candidate discipline, already used by the edge-aware runtime work `t_31d1c67f`/`t_36a87b51`).
- Scheduler tick / wake / authority / isolation / recovery primitives.
- Highest self-acceleration value: every downstream tranche depends on a trustworthy task/generation/runtime substrate.

### B1 — Runs / workers / observability / telemetry
- Worker spawn environment (`HERMES_PROFILE`, `HERMES_KANBAN_*`), runs/get/inspect, guarded terminate, heartbeat/stale/reclaim.
- Observability + telemetry substrate used to prove later tranches' behavior.

### B2 — Profiles / skills / model / capability routing
- Profile/skill discovery & validation, effective-toolsets routing, spawnability (`dispatcher_eligible` vs `end_to_end_observed`), capability routing.

### B3 — Control-plane / notifications
- Control-plane surface, notification subscribe/delivery contract (the closed `notify`/`notify+wake`/`wake`/`null` set per [BETA_DOGFOOD.md](../../docs/BETA_DOGFOOD.md)), delivery readback.

### B4 — Attachments / remote / polish
- Remote `content_base64` attachment transport, unified 25MB cap, and cross-cutting polish.
- Deliberately last: it is the least self-accelerating and benefits from B0–B3 runtime/observability maturity.

> B0–B4 are a *re-expression* of the existing W0–W4 long-range scope with an explicit self-acceleration ordering and rolling-promotion discipline layered on top. They do **not** redefine what W0–W4 contain.

---

## 4. Per-tranche lifecycle (uniform contract)

Every tranche B0–B4 follows the same gated lifecycle. "Dogfood" appears **twice** on purpose — first bounded, then integrated:

```
SPEC (intent + self-acceleration justification)
  -> IMPLEMENT (on the tranche's own candidate lane; never stable)
  -> TESTS (unit/integration/contract per IMPLEMENTATION_PLAN.md pyramid)
  -> INDEPENDENT REVIEW (separate reviewer; ACCEPT required)
  -> BOUNDED ACTIVATION (candidate-lane only; rollback armed)
  -> BOUNDED DOGFOOD (disposable hermes-chatgpt-e2e-* fixtures ONLY;
                      never the project board hermes-chatgpt-mcp)
  -> TRANCHE ACCEPT (own candidate/acceptance PASS; still NOT stable)
  ... (later, after all required tranches) ...
  -> INTEGRATED CANDIDATE assembly
  -> canary / MCP E2E / integrated dogfood
  -> Human Gate / stable ACCEPT
```

Each `->` is a gated transition; the prior step's completion does **not** authorize a later step, and a tranche's own ACCEPT never promotes it to `stable-current`.

---

## 5. Relationship to the existing critical path (not in conflict)

The rolling strategy **overlays** — it does not replace — the existing serial prerequisite spine. The mandatory pre-CUT3 chain is still serial and unchanged:

```
t_31d1c67f (fix) -> t_20dd938c (review) -> t_ef3ae8d4 (gate prep)
  -> authorized activation + live readback
  -> fresh upstream acceptance replacing historical t_47fcecec as needed
  -> t_235d884c (unfreeze) -> t_765c4305 (CUT3) -> hermes-v4-planning bootstrap
```

Rolling delivery says: *once CUT3 opens the bootstrap lane*, the W0–W4 work fans out into B0–B4 tranches that are individually promotable, rather than accumulated behind one big-bang cut. The fan-out→join→gate scheduling that makes this work-conserving is specified in the companion preflight `t_4b49ff1e` (`V4-RELEASE-CRITICAL-PATH-MAP.md`): fan-out after W0 REVIEW PASS, join at INTEGRATION, then candidate/canary/E2E/review/dogfood/promotion stays serial.

> Cross-link: `t_4b49ff1e` — `V4-RELEASE-CRITICAL-PATH-PREFLIGHT`. It classified the 48-card `hermes-v4-planning` board into mandatory serial spine + parallelizable waves + candidate/canary/review + Human Gate + post-release + optional research, and is the scheduling authority for *how* B0–B4 overlap safely. This strategy document is the *policy*; `t_4b49ff1e` is the *schedule*.

---

## 6. Final integrated gates are preserved (no erosion)

Rolling delivery adds early, bounded dogfood value but **preserves** the terminal integrated gates. Before anything reaches `stable-current`:

1. **Final integrated candidate** assembled from reviewed tranches (not a single tranche).
2. **Canary** with the fresh-session / provenance handshake ([CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md) §6): fresh MCP/OAuth session + observed receipt (canary/release ID, Connector SHA, Core SHA/version, schema/tool-surface version, scopes actually granted/effective); mismatch/unknown identity ⇒ FAIL before mutation.
3. **MCP E2E** PASS.
4. **Integrated dogfood** on disposable fixtures.
5. **Human Gate** — exact-revision, revision-bound authorization (separate from any provenance `GO`; a `GO` is evidence, not release authorization — [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md) §4).
6. **stable ACCEPT** — only now may `stable-current` be promoted, via the existing rollback-ready path.

A tranche that passed its own bounded dogfood is **not** a substitute for the integrated canary/E2E/Human-Gate/stable-ACCEPT sequence.

---

## 7. How this strategy lands in the canonical docs (review-gated, not direct)

Per invariant §2.2 (no direct commit-to-stable) and the rolling/independent-review philosophy, this strategy is committed to a **separate lane** `docs/v4-rolling-bootstrap-adopt` (branched from the protected `docs/v4-control-plane-source-of-truth-final` at `76cde68`) and submitted as a **pull request for independent review** against `docs/v4-control-plane-source-of-truth-final`. It is merged into the canonical docs lane only after that review ACCEPTs — exactly mirroring how a rolling tranche reaches promotion.

This card itself performs no direct mutation of `docs/v4-control-plane-source-of-truth-final`; the PR is the reviewed, bounded activation.

---

## 8. Cross-links (canonical)

- Delivery strategy policy: this document.
- Schedule / fan-out→join: `t_4b49ff1e` (`V4-RELEASE-CRITICAL-PATH-MAP.md`).
- Canonical V4 design + scope: [ROADMAP.md](ROADMAP.md) · [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) · [CURRENT_STATE.md](CURRENT_STATE.md).
- Source precedence / cold-start: [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md).
- Release-candidate truth-sync: [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md).
- DAG soft-retire contract (protected): [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md).
- Dogfood boundary + fixtures: [../../docs/BETA_DOGFOOD.md](../../docs/BETA_DOGFOOD.md) and [DOGFOOD_QA_PLAN.md](DOGFOOD_QA_PLAN.md).
- Evidence hierarchy + UNSAFE_TO_TEST: [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md).

---

## 9. Migration note — from old big-bang roadmap to rolling/bootstrap

| Aspect | Old big-bang posture (implicit) | New rolling/bootstrap canonical (this doc) |
|--------|--------------------------------|-------------------------------------------|
| Delivery unit | Whole V4 behind a single CUT3 | Independently promotable tranches B0–B4 |
| Dogfood timing | After all W0–W4 done | After each tranche's own implement+tests+review+bounded activation |
| Stable exposure | Direct, at the cut | Never direct; only via integrated candidate → canary → E2E → Human Gate → stable ACCEPT |
| Ordering driver | Wave enumeration W0–W4 | Self-acceleration value (B0 first) |
| Risk profile | One large promotion blast | Small, rollback-armed, review-gated tranches |
| Protected state | `stable-current` implicit | `stable-current` explicit invariant; no direct commit-to-stable |
| Relationship to W0–W4 | The plan | B0–B4 re-express the same scope with rolling discipline; W0–W4 content unchanged |

**What did NOT change:** the canonical V4 architecture, the P0/P1/P2/P3 feature scope, the final integrated gates (candidate/canary/E2E/dogfood/Human Gate/stable ACCEPT), the `stable-current` protection, and the serial pre-CUT3 prerequisite chain. Only the *delivery cadence and promotion discipline* changed.

*Authored by github-steward under task `t_4b01a9b7`. Review-gated PR against `docs/v4-control-plane-source-of-truth-final`; no live runtime/service/OAuth/barrier/CUT3/V4-board mutation performed.*
