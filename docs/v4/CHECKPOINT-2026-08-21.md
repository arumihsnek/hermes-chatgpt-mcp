# V4 / Phase-S Reconciliation Checkpoint — 2026-08-21

**Status:** DOCUMENTATION TRUTH-SYNC (supplemental to the canonical 2026-08-19 V4 design docs)
**Reconciliation date:** 2026-08-21 (UTC)
**Authored by:** github-steward (task `t_b6b71c9b`)
**Companion review card:** `t_4bb689c9` (DOCS-CHECKPOINT-REVIEW-20260821 — independent truth-sync audit)
**Documentation base (unchanged from canonical docs):** `9900c10` (local ref only; deployed connector SHA is **NOT_PROVEN** — see below)
**Scope of this document:** Bring canonical documentation up to the live 2026-08-21 Kanban state. This is a documentation truth-sync, NOT a new roadmap, NOT a product-scope change, NOT an authorization to build, deploy, or release.

---

## 0. How to determine current truth

Docs and the live ledger are different layers. Never treat this checkpoint as live task state after the reconciliation timestamp.

| Question | Authoritative source |
|----------|----------------------|
| Current task status / who is blocked / live execution order | **Hermes Kanban** (board `hermes-chatgpt-mcp`; cross-board items noted below). Task IDs are the ledger. |
| Canonical architecture / scope / declared plan | **Reviewed docs** in this `docs/v4/` set (dated 2026-08-19) plus this checkpoint. |
| Immutable candidate / release / build identity | **Build & provenance receipts** only (e.g. `RELEASE-SOURCE-PROVENANCE.md` chain, connector/Core SHAs surfaced at the canary handshake). Not claimed here. |
| Human release gate / promotion authorization | **Exact-revision human authorization** via the `t_4cf09578`-style revision-bound gate. A `GO` provenance preflight is NOT this authorization (see §4). |
| Connector discovery / live exposure | Operator-authoritative live MCP discovery (54 tools). Exposure ≠ validation (carried from canonical docs). |

> This document was reconciled at the timestamp above. Re-derive live status from Kanban before any decision. Docs that disagree with Kanban are stale; reference the supersession notes in §7 before trusting an older card.

---

## 1. Evidence references (verified to exist on the live boards)

All IDs below were checked against the live board databases at reconciliation time.

**Canonical V4 docs integration (this repo):**
- `t_043decc7` — V4-DOCS-INTEGRATE2 — canonical repo docs final integration (done). Branch `docs/v4-control-plane-source-of-truth-final`, commit `be903c60ca89a78d23e22311e7c9239031363c3b`, PR #2 (open against `beta/board-management`).
- `t_cd45cf2f` — V4-DOCS-REVIEW — independent evidence & architecture review (done, ACCEPT).

**Orchestration gap report (cross-board — `chatgpt-hermes-orchestration`):**
- `t_b67c9ab8` — DOGFOOD-DOC — materialize ChatGPT↔Hermes orchestration gap report in `my-hermes-config` (done). Repo `arumihsnek/my-hermes-config`, branch `docs/chatgpt-hermes-dogfood-gaps-20260821`, draft PR #49. Its original "Release triage note" said classification TBD; that is superseded by the 2026-08-21 decision trail (§5).

**Release triage + human decision:**
- `t_72108336` — V4-GAP-TRIAGE — map orchestration dogfood gaps onto beta/V4 (done). Human decision recorded in comment 579: **DO NOT convert all G1–G20 into beta blockers.**

**Outcome-gate implementation / recovery chain:**
- `t_b0901b4a` — KANBAN-GATE-REWORK — canonical fail-closed outcome-aware gating (status: **blocked / gave-up** after useful partial implementation; NOT a PASS — see §3).
- `t_c4c38028` — KANBAN-GATE-CLOSEOUT-A — freeze canonical outcome-gate candidate (running).
- `t_09f51d5a` — KANBAN-GATE-CLOSEOUT-B — adversarial + race verification of frozen outcome gate (todo).
- `t_8c125abe` — KANBAN-GATE-CLOSEOUT-C — reactivate exact-generation independent review (todo).
- `t_fc541b39` — KANBAN-GATE-REVIEW — independent acceptance of outcome-aware gating (blocked).
- `t_7c2f0fdd` — KANBAN-GATE-REAL-DOGFOOD — apply accepted gate to Phase-S DAG on a real board (todo).

**Provenance chain:**
- `t_415df0f5` — S-PROVENANCE-REVIEW-5 — independent review of corrected provenance (done, PASS).
- `t_dadd5ebf` — S-PREFLIGHT-5 — fresh GO/NO-GO preflight after provenance PASS (done). **This is a provenance-evidence GO only — it is explicitly NOT release/build/deploy authorization (see §4).**

**Hold rebind (current chain vs historical):**
- `t_e187bee7` — S-UNBLOCK-CHAIN-6 — rebind Phase-S hold to fresh GO + accepted outcome gate (todo). Depends on `t_7c2f0fdd` + `t_dadd5ebf`.
- `t_e1b6bae8` — S-UNBLOCK-CHAIN — older hold-release card tied to older recovery preconditions (todo). **Marked HISTORICAL / SUPERSEDED for the current release chain**; not deleted, not the current authority (see §7).

**Canary:**
- `t_be036abf` — S-CANARY-E2E — real MCP end-to-end validation against canary (todo). Comment 580 requires a fresh MCP/OAuth session before first mutation and a minimal observed receipt (see §6).

**V4 Wave ownership annotations (long-range, NOT Phase-S blockers):**
- `t_2656bd75` (Wave0 provenance/session identity), `t_5ae3cfd5` (Wave1 capability preflight), `t_bc1e909d` (Wave2 run/disposition provenance), `t_94a82805` (Wave3 durable remote attachments), `t_4cf09578` (Wave4 revision-bound human gates), `t_c2df0225` (extended dogfood finds/routes remaining debt).

---

## 2. Current critical path (immediate Phase-S release candidate)

This is the only current blocking chain for immediate Phase-S. It is distinct from the long-range V4 roadmap (§5).

```
outcome-gate candidate closeout (t_c4c38028)
  -> adversarial / race verification (t_09f51d5a)
  -> exact-generation independent review (t_fc541b39)
  -> real-board gate dogfood (t_7c2f0fdd)
  -> hold rebind to fresh GO + accepted gate (t_e187bee7)
  -> clean build (identity-pinned)
  -> rollback-ready
  -> canary
  -> fresh-session / provenance handshake (new MCP/OAuth session + observed receipt)
  -> canary E2E (t_be036abf)
  -> exact-release human gate (revision-bound, t_4cf09578-style)
  -> traffic switch
  -> post-switch smoke
  -> release acceptance
  -> V4 cut (baseline freeze)
```

Each `->` is a gated transition. No step is "done" until its own evidence exists; the prior step's completion does not authorize a later step.

---

## 3. Current blocker — G1 / outcome-aware dependency authorization

- **G1** (outcome-aware dependency authorization) is the *only* substantive new platform correction blocking immediate Phase-S per the 2026-08-21 triage.
- Historical record: `t_b0901b4a` **blocked / gave-up** after a useful partial implementation. It is represented here as **partial / gave-up with a successor chain**, never as PASS.
- Successor chain (authoritative for the current gate):
  `t_b0901b4a` (gave-up) → `t_c4c38028` (freeze candidate) → `t_09f51d5a` (adversarial/race) → `t_8c125abe` (reactivate review) → `t_fc541b39` (independent ACCEPT) → `t_7c2f0fdd` (real-board dogfood).
- Until `t_fc541b39` returns an independent ACCEPT and `t_7c2f0fdd` proves the gate on a real board, the outcome-gate closeout is **NOT_PROVEN** and the hold rebind `t_e187bee7` cannot be satisfied.

---

## 4. GO provenance evidence ≠ release authorization (explicit)

- `t_dadd5ebf` produced a **GO provenance preflight** — a statement that the Phase-S source/provenance bundle is internally consistent and durably reproducible.
- That GO is **evidentiary only**. It does **NOT** authorize: building for production, deploying, canarying, switching traffic, or releasing.
- The exact-release human gate is a separate, revision-bound authorization (see §1, §2) that must be granted on the exact frozen candidate SHA. No document in this `docs/v4/` set, including this checkpoint, constitutes that authorization.

---

## 5. Phase-S vs V4 horizons (preserved)

**Decision (2026-08-21, comment 579 on `t_72108336`):** Do NOT pull G1–G20 wholesale into Phase-S blockers.
- G1 is the only substantive *new platform correction* blocking immediate Phase-S.
- A minimal set of **fresh-session / provenance test-integrity** requirements is required for immediate E2E (the fresh-session/provenance handshake, §6).
- All remaining gaps (G2–G20) belong to existing V4 waves, the dogfood program, or other boards (cross-board ownership below). They are tracked, not blocking immediate Phase-S, unless a concrete release-safety regression is proven.

### Immediate-E2E coverage vs later architecture
- **G2 / G6 / G14 / G15 / G16** are *minimally covered at immediate E2E* via the fresh-session/provenance handshake (identity/scope readback, observed receipt). Their **full identity/session architecture remains later Wave0+ / other layers** — do not claim those gaps are closed by the handshake alone.
- G3–G5 (Hermes Core / control-plane regressions), G7 (auth principal separation), G8 (Wave1), G9/G10 (Profile Factory / model intelligence), G11 (Wave3), G12 (Wave2), G13 (cross-layer reconciliation), G17 (Phase-S exact-release minimum + control-plane full), G18/G19 (orchestration), G20 (governance regression) are tracked in their owning waves/boards and are not immediate Phase-S blockers absent a proven release-safety regression.

### Cross-board ownership (live, not blocking immediate Phase-S unless a regression is proven)
- G18 / G19: `chatgpt-hermes-orchestration`
- Telegram transport / full human-gate UX: `hermes-control-plane`
- Model / routing intelligence: `Profile Factory`

### Long-range roadmap (intact — do not re-plan here)
```
stable release acceptance
  -> V4 cut
  -> tranche bootstrap
  -> Waves 0..4: IMPLEMENT / TEST / DOGFOOD / REVIEW
  -> candidate integration / clean build / canary / MCP E2E
  -> independent ACCEPT-FOR-DOGFOOD
  -> extended dogfood + incident remediation lane
  -> exact human promotion gate
  -> traffic switch
  -> post-switch smoke
  -> stable accept
  -> post-V4 truth sync / hardening / research
```
This long-range flow is owned by the V4 Wave cards (`t_2656bd75`…`t_c2df0225`) and is compatible with, not in conflict with, the immediate Phase-S critical path in §2.

---

## 6. S-CANARY-E2E — fresh-session / provenance handshake (t_be036abf, comment 580)

Before the canary's first mutation:
1. Establish a **fresh MCP/OAuth session** (no reused token/session from prior QA).
2. Capture a **minimal observed receipt**:
   - expected canary / release ID
   - Connector SHA
   - Core SHA / version
   - schema / tool-surface version
   - scopes **actually granted / effective** (not merely requested)
3. **Mismatch or unknown identity ⇒ FAIL before any mutation.** Do not proceed; do not write to the live board.

This handshake is the immediate-E2E bridge for G2/G6/G14/G15/G16 (see §5) and is a prerequisite gate, not a substitute for their later full architecture.

---

## 7. Supersession notes (so old cards are not mistaken as current authority)

- **`t_e1b6bae8`** (S-UNBLOCK-CHAIN) — HISTORICAL / SUPERSEDED for the current release chain. It is tied to older recovery preconditions that the `t_b0901b4a` → `t_c4c38028` chain replaced. It remains in the DB (not deleted), but `t_e187bee7` is the current hold-rebind authority.
- **Old "Release triage note" (TBD)** on `my-hermes-config` PR #49 — superseded by the 2026-08-21 decision trail in this checkpoint and by `t_72108336` comment 579.
- **Canonical 2026-08-19 V4 docs** — remain authoritative for design/scope/architecture. This checkpoint supplements them with live release-candidate state; where they conflict on *release-candidate* status, Kanban (live) wins and the doc should be re-reconciled.
- **`t_b0901b4a`** — partial/gave-up with successor chain; never read as a completed gate.

---

## 8. Gap → owner table (compact)

| Gap | Disposition for immediate Phase-S | Owner / lane |
|-----|-----------------------------------|--------------|
| G1 | **Immediate blocker** — outcome-aware dependency authorization | recovery chain `t_c4c38028`→`t_fc541b39`→`t_7c2f0fdd` |
| G2 / G6 / G14 / G15 / G16 | Immediate test integrity (fresh-session/provenance handshake) + later full architecture | Wave0+ / other layers |
| G3 / G4 / G5 | Hermes Core / control-plane regressions | Hermes Core / control-plane |
| G7 | Auth principal separation | control-plane |
| G8 | Wave1 | `t_5ae3cfd5` |
| G9 / G10 | Profile Factory / model intelligence | Profile Factory |
| G11 | Wave3 | `t_94a82805` |
| G12 | Wave2 | `t_bc1e909d` |
| G13 | Cross-layer reconciliation | cross-layer |
| G17 | Phase-S exact-release minimum + control-plane full | control-plane |
| G18 / G19 | Orchestration | `chatgpt-hermes-orchestration` |
| G20 | Governance regression | governance |

None of G2–G20 are wholesale beta blockers per the 2026-08-21 decision.

---

## 9. Completed checkpoints (evidence-anchored)

- Canonical V4 docs ACCEPT — `t_cd45cf2f` (independent review).
- Provenance review PASS — `t_415df0f5` (independent review of corrected provenance).
- Fresh provenance preflight GO — `t_dadd5ebf` (provenance evidence GO **only**; not release authorization — §4).

## 10. Next semantic checkpoints (not yet passed)

1. Independent outcome-gate ACCEPT — `t_fc541b39`.
2. Real-board gate proof — `t_7c2f0fdd`.
3. Clean-build identity (pinned SHA, rollback-ready).
4. Canary E2E PASS — `t_be036abf` (with fresh-session handshake, §6).
5. Human release decision (exact-revision authorization).
6. Stable acceptance.
7. V4 baseline freeze.

## 11. Material NOT_PROVEN / residual risks still active

- Exact deployed connector SHA — **STILL_NOT_PROVEN** (carried from canonical docs; must be pinned at clean-build identity, §10.3).
- Outcome-gate closeout — **NOT_PROVEN** until `t_fc541b39` ACCEPT + `t_7c2f0fdd` real-board proof.
- G1 outcome-aware dependency authorization — **blocked** (this checkpoint's current blocker, §3).
- Full identity/session architecture for G2/G6/G14/G15/G16 — **NOT_PROVEN at full depth**; only immediate-E2E handshake coverage exists.
- Live HTTP/API auth & reachability, dashboard plugin live mount, provider/model validity — **STILL_NOT_PROVEN** (canonical docs §2).
- All canonical "UNSAFE_TO_TEST" items — unresolved by safety classification, not by evidence.
- Release authorization — **NOT_GRANTED**; no document here authorizes build/deploy/release.

---

*Reconciliation performed by github-steward under task `t_b6b71c9b`. Companion independent audit: `t_4bb689c9`. Re-derive live status from Kanban before any decision; this checkpoint is a point-in-time truth-sync, not live task state.*
