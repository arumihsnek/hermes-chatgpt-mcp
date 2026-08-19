# Stale Documentation Inventory

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE
**Last reconciled:** 2026-08-19
**Documentation base:** 9900c10 (local ref only; deployed SHA NOT_PROVEN)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)
**Derived from:** t_4d983898 (`STALE-DOCS-INVENTORY.md`)

---

## Classification Key

- **SUPERSEDE:** do not use as current-state authority after the V4 set is accepted.
- **RETAIN / LINK:** useful as a dated contract, procedure, architecture record, or evidence artifact; preserve its date and scope.
- **REVALIDATE:** operational or version-sensitive claims require a fresh evidence run before being presented as current.

Historical does not mean incorrect within its original scope. It means the document must not silently override the current evidence-bound V4 set.

---

## Inspected Repository Documents

| Path | Classification | Stale boundary | Canonical action |
|------|----------------|-----------------|------------------|
| `README.md` | RETAIN / LINK; REVALIDATE for V4 | Describes the v0.4 public surface as seven READ tools plus `create_task`; incomplete for V4 | Add the V4 link; retain v0.4 usage contract and version-bound language |
| `docs/architecture/HERMES-INTEGRATION.md` | RETAIN / LINK; REVALIDATE | Dated 2026-08-16 and reports Hermes v0.20.1 | Keep as v0.4 integration record; link V4 architecture and do not use v0.20.1 as current |
| `docs/REVIEW.md` | RETAIN / LINK as dated review; REVALIDATE current PASS claims | Reports dated v0.4 tests/deployment recheck; current deployed SHA/reachability remain STILL_NOT_PROVEN | Preserve historical test evidence; require new V4 review |
| `docs/DEPLOYMENT.md` | RETAIN / LINK; REVALIDATE status only | Installation/systemd/OpenResty/runbook does not establish deployed connector SHA or reachability | Retain operational procedure; link from V4 release sections |
| `docs/SECURITY.md` | RETAIN / LINK; VERSION-BOUND | Documents v0.4 eight-tool allowlist and scopes, not V4 inventory | Retain v0.4 security contract; add V4 security delta when surface changes |
| `docs/evidence/MULTIBOARD-GLOBAL-READ-ONE-BOARD-WRITE-2026-08-16.md` | RETAIN / LINK as dated evidence | Dated multi-board evidence | Preserve unchanged; cite with date and scope |
| `docs/evidence/OAUTH-CREATE-SCOPE-DIAGNOSIS-2026-08-16.md` | RETAIN / LINK as dated evidence | Orthogonal dated OAuth diagnosis | Preserve unchanged; do not promote to current registry |

---

## Historical Design and Plan Documents

| Path | Classification | Stale boundary | Canonical action |
|------|----------------|-----------------|------------------|
| `docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-design.md` | SUPERSEDE for current design; RETAIN as history | v0.1 read-only six-tool/no-mutation design | Keep as evolution history; V4 spec is current |
| `docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp.md` | SUPERSEDE for execution planning; RETAIN as history | v0.1 six-tool implementation plan | Retain as historical provenance; use V4 implementation plan |
| `docs/superpowers/specs/2026-08-16-hermes-chatgpt-mcp-v03-multiboard-design.md` | SUPERSEDE for current design; RETAIN as history | v0.3 design, Hermes v0.20.1 and older integration baseline | Preserve decision record; do not use version/SHA as current |
| `docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp-v03-multiboard.md` | SUPERSEDE for execution planning; RETAIN as history | v0.3 plan constrained surface to `list_boards` plus `create_task` | Preserve completed plan; V4 plan governs current work |

---

## Other Dated Root/Task Artifacts

Dated `VERIFICATION-*`, `REPORT-*`, and `PLAN-*` files at the repository root are **dated task evidence or historical plans**, not current source-of-truth material. They remain archival references requiring per-file provenance when cited. This inventory does not infer their contents from filenames.

---

## Canonical Information Architecture

1. **Current-state index:** `docs/v4/README.md` and `docs/v4/CURRENT_STATE.md`.
2. **V4 design/spec:** `CONTROL_PLANE_SPEC.md` and `MCP_TOPOLOGY_ADR.md`.
3. **Current capability references:** `TOOL_CATALOG.md`, `v4-tool-catalog.json`, `KANBAN_CLI_MATRIX.md`, `HERMES_CAPABILITIES_MATRIX.md`, `capability-index.json`.
4. **Planning and QA:** `ROADMAP.md`, `IMPLEMENTATION_PLAN.md`, and `DOGFOOD_QA_PLAN.md`.
5. **Evidence and uncertainty:** `EVIDENCE_AND_OPEN_QUESTIONS.md`.
6. **Historical evidence:** Existing dated docs remain at their original paths and are linked with dates/scope.

### Update rule

Every current-state claim must include Hermes version, local HEAD or deployed SHA. If the deployed connector SHA cannot be pinned, state **STILL_NOT_PROVEN**. Do not infer it from `Kanban_Beta` discovery metadata.

---

## Do Not Silently Correct

- v0.4 docs may remain accurate for their documented v0.4 scope while incomplete for V4.
- Historical docs' version/commit claims are preserved as historical claims, not overwritten.
- `Kanban_Beta` is retained only as stale naming metadata; controller evidence classifies deployment as STABLE.
- Live connector exact SHA, live HTTP auth/reachability, and unsafe mutation paths remain explicitly unresolved.
