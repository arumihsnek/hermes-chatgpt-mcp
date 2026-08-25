# V4 Control-Plane Documentation

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19 (canonical design) + **2026-08-21 release-candidate truth-sync** (see [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md))
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)

> **Truth-sync note (2026-08-21):** The canonical 2026-08-19 design docs below remain authoritative for architecture/scope. A supplemental reconciliation checkpoint brings them up to the live Kanban release-candidate state: [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md). Docs are a point-in-time snapshot; current task status always comes from Kanban. A provenance `GO` (e.g. `t_dadd5ebf`) is evidence, not release authorization.

---

## Index

| Document | Purpose | Status |
|----------|---------|--------|
| [CURRENT_STATE.md](CURRENT_STATE.md) | Canonicalized source of truth — evidence hierarchy, inventories, uncertainty ledger | Canonical |
| [CONTROL_PLANE_SPEC.md](CONTROL_PLANE_SPEC.md) | Corrected V4 tool contract with exact current OAuth scopes | Canonical |
| [MCP_TOPOLOGY_ADR.md](MCP_TOPOLOGY_ADR.md) | ADR: Single MCP + privilege-separated internal adapters | Canonical |
| [TOOL_CATALOG.md](TOOL_CATALOG.md) | Final 79-entry MCP tool catalog with product status vocabulary | Canonical |
| [v4-tool-catalog.json](v4-tool-catalog.json) | Machine-readable catalog index | Canonical |
| [KANBAN_CLI_MATRIX.md](KANBAN_CLI_MATRIX.md) | 47-entry CLI→MCP matrix; registration ≠ behavioral PASS | Canonical |
| [HERMES_CAPABILITIES_MATRIX.md](HERMES_CAPABILITIES_MATRIX.md) | Native Hermes tool/skill/profile registry matrix | Canonical |
| [capability-index.json](capability-index.json) | Machine-readable capability index | Canonical |
| [ROADMAP.md](ROADMAP.md) | Corrected P0-P3/DO_NOT_EXPOSE roadmap | Canonical |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Implementation plan with testing pyramid and release gates | Canonical |
| [DOGFOOD_QA_PLAN.md](DOGFOOD_QA_PLAN.md) | MCP-as-SUT dogfood plan; disposable fixture boards only | Canonical |
| [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) | Evidence hierarchy, STILL_NOT_PROVEN/UNSAFE_TO_TEST, dogfood incidents | Canonical |
| [STALE_DOCS.md](STALE_DOCS.md) | Canonicalized stale-document inventory | Canonical |
| [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md) | **2026-08-21 release-candidate truth-sync** — Phase-S critical path, blockers, GO≠authorization, gap→owner | Reconciliation (supplemental) |
| [RECOVERY-TRUTH-SYNC-2026-08-24.md](RECOVERY-TRUTH-SYNC-2026-08-24.md) | **2026-08-24 recovery truth-sync** — invalid historical restore, 165d current state, pinned baseline, fresh gate, MCP P0 | Reconciliation (supplemental) |
| [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md) | **2026-08-25 current-truth freshness** — Source Precedence Ladder, cold-start protocol, Project Model vs Current State Vector, dogfood finding | Reconciliation (supplemental) |

---

## Evidence Hierarchy & Source-of-Truth Rules

0. **Source precedence (cold-start rule):** live runtime readback > live Kanban/runs/events > fresh immutable evidence bound to exact SHA/run > current Git HEAD/worktrees/refs > current checkpoints/manifests > current repo docs > historical terminal cards > archived/superseded cards > old docs > project/harness memory > inference. A lower rank never overrides a higher one; on conflict mark the lower **STALE**. A checked-out doc tree is **not** automatically truth.

1. **Primary (canonical):** Local read-only investigations completed 2026-08-19 (tasks t_2d568471 + 7 parents, t_4d983898, t_484d4ab0, t_4ce4ba8f, t_8a7b081c, t_1419658e). No public research, no repo mutations.
2. **Authoritative live discovery:** Operator-authoritative connector discovery 2026-08-19 (54 tools exposed). Exposure ≠ validation.
3. **Behavioral validation:** Only actual tool invocation in this docs session or prior board QA constitutes `AVAILABLE_VALIDATED`. Discovery-only tools are `NOT_PROVEN`.
4. **Stale docs:** Historical v0.1/v0.3/v0.4 docs retained as dated contracts; never allowed to override newer source-bound findings without revalidation.
5. **Deployed SHA:** Exact deployed connector SHA is **STILL_NOT_PROVEN**. `Kanban_Beta` discovery label is stale metadata; controller classifies deployment as STABLE.
6. **Scope vocabulary:** Current proven scopes: `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, `offline_access` (connection-only). Finer scopes are PROPOSED only.
7. **Registration ≠ PASS:** CLI `--help` registration proves parser existence only. Behavioral status requires safe read call, board evidence, or MCP E2E test.

---

## Navigation

- **Start here:** [CURRENT_STATE.md](CURRENT_STATE.md) for the canonical evidence-bound current state
- **Specs:** [CONTROL_PLANE_SPEC.md](CONTROL_PLANE_SPEC.md) + [MCP_TOPOLOGY_ADR.md](MCP_TOPOLOGY_ADR.md)
- **Catalog:** [TOOL_CATALOG.md](TOOL_CATALOG.md) + [v4-tool-catalog.json](v4-tool-catalog.json)
- **Matrices:** [KANBAN_CLI_MATRIX.md](KANBAN_CLI_MATRIX.md) + [HERMES_CAPABILITIES_MATRIX.md](HERMES_CAPABILITIES_MATRIX.md)
- **Planning:** [ROADMAP.md](ROADMAP.md) + [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) + [DOGFOOD_QA_PLAN.md](DOGFOOD_QA_PLAN.md)
- **Evidence & History:** [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) + [STALE_DOCS.md](STALE_DOCS.md)
- **2026-08-21 release-candidate truth-sync:** [CHECKPOINT-2026-08-21.md](CHECKPOINT-2026-08-21.md)
- **2026-08-24 recovery truth-sync:** [RECOVERY-TRUTH-SYNC-2026-08-24.md](RECOVERY-TRUTH-SYNC-2026-08-24.md)
- **2026-08-25 current-truth freshness (source precedence):** [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)

---

## Provenance

Derived from kanban tasks:
- **SoT & Stale Inventory:** t_4d983898 (`SOURCE-OF-TRUTH-DRAFT.md`, `STALE-DOCS-INVENTORY.md`)
- **Corrected Spec/ADR:** t_484d4ab0 (`V4-CONTROL-PLANE-SPEC-DRAFT.md`, `MCP-TOPOLOGY-ADR-DRAFT.md`)
- **Matrices/Index:** t_4ce4ba8f (`HERMES-KANBAN-CLI-MATRIX-DRAFT.md`, `HERMES-NATIVE-CAPABILITIES-MATRIX-DRAFT.md`, `capability-index.json`)
- **Roadmap/Impl/Dogfood:** t_8a7b081c (`V4-ROADMAP-DRAFT.md`, `V4-IMPLEMENTATION-PLAN-DRAFT.md`, `V4-DOGFOOD-QA-PLAN-DRAFT.md`)
- **Tool Catalog:** t_1419658e (`V4-TOOL-CATALOG-DRAFT.md`, `v4-tool-catalog.json`)
- **Synthesis & Local Research:** t_2d568471 + parents (t_c2257b50, t_2d78d03f, t_59a2a2f5, t_ad6925aa, t_ef94f514, t_2499ad0a, t_5caf4595)
