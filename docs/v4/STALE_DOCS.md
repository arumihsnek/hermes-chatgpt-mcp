# Stale Documentation Inventory

**Status:** CANONICAL V4 DESIGN / CURRENT EVIDENCE + **V4 STABLE ACCEPTED 2026-08-27**
**Last reconciled:** 2026-08-19 + **2026-08-25 DAG soft-retire contract** (see [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)) + **2026-08-27 V4 stable truth-sync** (see [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) + [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md))
**Documentation base (pre-V4-stable design docs):** 9900c10 (local ref only; pre-V4 beta worktree — **NOT** the V4 stable commit)
**V4 stable connector (durable binding):** `4ae5060931a64741185c5c8deb3886a5901f21cc` (short `4ae5060`, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`, Hermes Core MCP baseline `d7eba25ea8f6`)
**See also:** [README.md](README.md) | [CURRENT_STATE.md](CURRENT_STATE.md) | [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) | [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) | [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md)
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
| `README.md` (root, "seven READ tools plus one WRITE") | RETAIN / LINK; REVALIDATE for current runtime | v0.4 public surface count; current live MCP surface is **54 tools** | Label as v0.4; never present as current runtime without qualification |
| `docs/SECURITY.md` ("eight-tool allowlist") | RETAIN / LINK; VERSION-BOUND; REVALIDATE for current runtime | v0.4 eight-tool allowlist; V4 inventory is 54 tools | Retain v0.4 security contract; flag as not-current-runtime |
| `docs/DEPLOYMENT.md` ("beta exposes eleven tools") | RETAIN / LINK; REVALIDATE for current runtime | Dated v0.x tool count; not current runtime count | Retain operational procedure; qualify any tool-count claim |
| `docs/architecture/HERMES-INTEGRATION.md` ("eleven tools total") | RETAIN / LINK; REVALIDATE for current runtime | Dated 2026-08-16 v0.4 count; superseded by 54-tool discovery | Keep as v0.4 integration record; flag as not-current |
| `docs/evidence/BETA-BOARD-MANAGEMENT-PLAN-2026-08-16.md` ("eleven tools") | RETAIN / LINK as dated plan | Dated beta plan tool count | Preserve as history; do not present as current |
| `docs/superpowers/plans/2026-08-16-hermes-chatgpt-mcp-beta.md` ("eight stable / eleven beta") | RETAIN / LINK as dated plan | Dated plan tool counts | Preserve as history; do not present as current |

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
6. **DAG / projection contract:** `DAG-SOFT-RETIRE-CONTRACT.md` (soft-retire `edge_state`, PROJECTION_RUNTIME_P0).
7. **Historical evidence:** Existing dated docs remain at their original paths and are linked with dates/scope.

### Update rule

Every current-state claim must include Hermes version, local HEAD or deployed SHA. If the deployed connector SHA cannot be pinned, state **STILL_NOT_PROVEN**. Do not infer it from `Kanban_Beta` discovery metadata.

---

## Do Not Silently Correct

- v0.4 docs may remain accurate for their documented v0.4 scope while incomplete for V4.
- Historical docs' version/commit claims are preserved as historical claims, not overwritten.
- `Kanban_Beta` is retained only as stale naming metadata; controller evidence classifies deployment as STABLE.
- Live connector exact SHA, live HTTP auth/reachability, and unsafe mutation paths remain explicitly unresolved.

---

## V4 stable reclassification (2026-08-27)

The 2026-08-27 V4 stable acceptance changed the classification of some claims that the 2026-08-19 canonical design flagged as `NOT_PROVEN` or `STILL_NOT_PROVEN`. The reclassification is **evidence-bound** (live readback of 3 surfaces, 4 on-disk SHA-256 manifest pins, 8/8 prerequisites PASS). The full reconciliation is in [CHECKPOINT-2026-08-27-V4-STABLE.md](CHECKPOINT-2026-08-27-V4-STABLE.md) and the short anchor in [RELEASE-STABLE-V4.md](../../RELEASE-STABLE-V4.md).

| Prior classification (2026-08-19 / 2026-08-25) | New classification (2026-08-27) | Evidence |
|----------------------------------------------|----------------------------------|----------|
| `Deployed connector SHA: STILL_NOT_PROVEN` (in `CURRENT_STATE.md` §2 + §11, `EVIDENCE_AND_OPEN_QUESTIONS.md` §2) | **RESOLVED** — durably bound to `4ae5060931a64741185c5c8deb3886a5901f21cc` (V4 stable, branch `v4-candidate-integration`, surface `beta`, API `v4.wave0`) | live readback (3 surfaces, all 4 headers match); 4 on-disk SHA-256 manifest pins matching R2; 8/8 prerequisites PASS |
| `Live HTTP/API auth and reachability: STILL_NOT_PROVEN` (in `EVIDENCE_AND_OPEN_QUESTIONS.md` §2) | **PARTIALLY RESOLVED** — public origin reachability proven for `/healthz`, `/mcp` (401 with bearer challenge), and OAuth discovery. Full native API surface (dashboard plugin mount, native Hermes REST) remains `STILL_NOT_PROVEN`. | live readback; see [CHECKPOINT-2026-08-27-V4-STABLE.md §1a](CHECKPOINT-2026-08-27-V4-STABLE.md) |
| `Live MCP tool count: 54` (2026-08-19 discovery) | **UPDATED** — `4ae5060` exposes **66 raw tools** reproducibly today (reconciled 2026-08-28; see [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](CHECKPOINT-2026-08-27-V4-STABLE.md) + `t_f30cf660` §3.1). The historical post-switch smoke `t_a47fd88f` (2026-08-26 14:34 UTC) reported **71**; the 5-tool delta is transient / not reproducible against the same `4ae5060` today. The ChatGPT-visible / invocable surface is **11** (frozen by `t_01200e57`) and is **not** equal to raw `tools/list`. All 6 v4.wave0 required tools present (subset of the 11) | `t_a47fd88f` contract check #10 (historical 71) + `t_f30cf660` §3.1 (reproducible 66) + `t_01200e57` (frozen 11) |
| v0.4 `docs/DEPLOYMENT.md` + `docs/SECURITY.md` `8791` topology descriptions | **RETAIN / LINK; SUPERSEDE for current runtime** — preserved as **dated v0.4 contract**; a new `## V4 stable runtime (2026-08-27)` section in those files points readers at the V4 stable truth | live readback (no process on 8791; 8789 is override-redirected; 8792 is the canary) |
| `Kanban_Beta` discovery label is "stale metadata; controller classifies deployment as STABLE" | **UPDATED** — narrative preserved; the **on-disk build.json `surface` value is now `beta`** (not `stable`); controller still classifies as STABLE; documented residual (no contract violation) | live readback; `t_a47fd88f` POST_SWITCH_REPORT residual note |

### Newly documented residuals (non-blocking, durable in V4 stable)

| # | Residual | Severity | Source |
|---|----------|----------|--------|
| 1 | F-DOGFOOD-01 `bounded_log` cursor `BACKEND_ERROR` (additive convenience only) | LOW, fail-closed | `t_45647dc7` extended dogfood |
| 2 | W0 Low `initialize` 1999-01-01 negotiates 2025-11-25 | LOW | `t_068740be` independent review |
| 3 | Ephemeral worker venv `hermes_cli` `ModuleNotFoundError` (canary venv only) | LOW | canary-side observation |
| 4 | `deployed_at` reports canary's original deploy time, not 2026-08-27 cutover time | Informational | `t_a47fd88f` POST_SWITCH_REPORT |
| 5 | No `/opt/hermes-chatgpt-mcp` (stable checkout dir); rollback uses venv only | Informational | `t_1e84eb11` parent handoff |
| 6 | Pre-V4 `hermes-chatgpt-mcp-beta.service` (8791) dormant in V4 stable topology | Informational | live readback |

These residuals are **not** V4 stable blockers. They are documented in [CHECKPOINT-2026-08-27-V4-STABLE.md §6](CHECKPOINT-2026-08-27-V4-STABLE.md), [CURRENT_STATE.md §17.6](CURRENT_STATE.md), and [EVIDENCE_AND_OPEN_QUESTIONS.md §9](EVIDENCE_AND_OPEN_QUESTIONS.md).

### Pre-promotion backups (preserved, byte-anchored rollback targets)

These on-disk backups are the **prior-good** state to revert to if the V4 stable is rolled back. They are NOT the V4 stable; they are the **byte-anchored rollback targets** documented in [CHECKPOINT-2026-08-27-V4-STABLE.md §1c](CHECKPOINT-2026-08-27-V4-STABLE.md).

| Backup | Commit | Surface | Deployed at | Role |
|--------|--------|---------|--------------|------|
| `/var/lib/hermes-chatgpt-mcp/build.json.pre-surface-rectification-20260826T103951Z.bak` | `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` | `stable` | 2026-08-25T15:13:56Z | Immediate prior-good (the rollback target) |
| `/var/lib/hermes-chatgpt-mcp/build.json.pre-edge-state-20260825T1440Z.bak` | `dc25e8bf7a66be87e12da33613d83c874be50038` | `stable` | 2026-08-24T19:35:56Z | Prior-before-the-prior (recovery-mutation generation; not the rollback target) |
