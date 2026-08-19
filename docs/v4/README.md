# V4 Documentation — Canonical Source of Truth

This directory contains the canonical documentation for Hermes ChatGPT MCP V4, integrated from authoritative parent tasks.

## Files

- `README.md` — This file
- `CURRENT_STATE.md` — Authoritative runtime/current connector state + evidence ledger
- `CONTROL_PLANE_SPEC.md` — V4 tool/API contracts and safety model
- `MCP_TOPOLOGY_ADR.md` — One MCP vs companion MCPs decision
- `TOOL_CATALOG.md` — P0/P1/P2/P3/DO_NOT_EXPOSE catalog
- `KANBAN_CLI_MATRIX.md` — Exhaustive Kanban actions
- `HERMES_CAPABILITIES_MATRIX.md` — Exhaustive native Hermes capabilities
- `ROADMAP.md` — Release timeline and milestones
- `IMPLEMENTATION_PLAN.md` — Step-by-step implementation guide
- `DOGFOOD_QA_PLAN.md` — Validation and quality assurance strategy
- `EVIDENCE_AND_OPEN_QUESTIONS.md` — Supporting evidence and unresolved items
- `v4-tool-catalog.json` — Machine-readable tool catalog
- `capability-index.json` — Machine-readable capability index

## Source of Truth

This documentation integrates the following parent artifacts:
- Tool Catalog: `t_1419658e` (final artifacts)
- Roadmap/Implementation/Dogfood: `t_8a7b081c` (final artifacts)
- Spec/ADR: `t_484d4ab0` (corrected artifacts)
- Source of Truth: `t_4d983898`
- Matrices: `t_4ce4ba8f` (normalized against live discovery)

## Status

Based on branch `docs/v4-control-plane-source-of-truth-work` from local base `9900c10` (docs: record verified beta dogfood release).

**Important**: The exact deployed connector SHA remains `STILL_NOT_PROVEN`. The live connector surface is classified as `STABLE` per controller evidence, but the label `Kanban_Beta` is stale metadata.

Last updated: 2026-08-19