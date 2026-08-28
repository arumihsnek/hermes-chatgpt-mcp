# V4 Stable — Release Provenance

**Status:** POST-V4 STABLE RELEASE PROVENANCE (durable cross-document anchor)
**Authored by:** github-steward (task `t_ca2ba9ae`)
**Release date:** 2026-08-27 (UTC)
**Documentation base:** 4ae5060931a64741185c5c8deb3886a5901f21cc (V4 stable commit, NOT a documentation-only commit; the V4 stable itself is the docs base)
**See also:** [CHECKPOINT-2026-08-27-V4-STABLE.md](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) — full truth-sync checkpoint, including live readback, topology, rollback, residuals, dogfood lessons.

> This is a **short, durable** release-provenance anchor. It is the single-page summary that any future V4.x release doc, ADRs, runbooks, or external communication should link to. The full evidence chain lives in the parent task `t_1e84eb11` (ACCEPT 2026-08-27) and the checkpoint above.

---

## Release identity (the V4 stable)

| Field | Value |
|-------|-------|
| **Connector (V4 stable commit)** | `4ae5060931a64741185c5c8deb3886a5901f21cc` |
| Connector short SHA | `4ae5060` |
| Connector branch | `v4-candidate-integration` |
| Connector commit message | `fix(integration): resolve cross-wave residuals — board-scoped attachments (FS drift) + cursor paging wired (Wave-2 F1)` |
| Connector commit date | 2026-08-26T14:01:53Z |
| **Phase-S source bundle** (`release/source-bundle-phase-s` in the same repo) | `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` |
| Phase-S bundle short SHA | `9a8410b4` |
| Phase-S bundle commit message | `fix: add PyYAML runtime dependency for kanban_diagnostics import` |
| Phase-S bundle commit date | 2026-08-19T23:12:54Z |
| **Hermes Core MCP baseline** (response header) | `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92` (header short `d7eba25ea8f6`) |
| **Hermes Core baseline branch** (response header) | `v4/baseline-post-update-885e9ef` (Hermes Core short `885e9ef73829`) |
| **Phase-S short SHA** (parent handoff) | `ef22b89e8b49` |
| **API surface version** (response header `x-api-version`) | `v4.wave0` |
| **V4 provenance header** (response header `x-v4-provenance`) | `4ae5060931a6/d7eba25/beta` |
| **Surface** (build.json) | `beta` (controller classifies the deployment as STABLE; `Kanban_Beta` discovery label is stale naming metadata) |
| **Live raw MCP `tools/list` tool count** (reproducible 2026-08-28) | **66** distinct names (35 unique `@mcp.tool(name=...)` decorators after FastMCP last-wins dedup of the two `list_boards` registrations + 31 unique `register_canonical(...)` names) — see [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) for the reconciliation with the historical 71 and the ChatGPT 11-tool contract |
| **Live raw MCP `tools/list` tool count** (historical post-switch smoke, 2026-08-26 14:34 UTC) | **71** (transient measurement; not reproducible against the same `4ae5060` today; the 5-tool delta is documented in the §5.1 link above) |
| **ChatGPT-visible / invocable surface** (frozen projection) | **11** tools (the `t_01200e57` ChatGPT session-compatibility contract; OpenAI's MCP connector filters `tools/list` and pins what it offers; **not equal to raw `tools/list`**) |
| **v4.wave0 required tools** (all 6 present) | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` |
| **deployed_at** (build.json) | `2026-08-26T14:34:00Z` — canary's original deploy time, **not** the 2026-08-27 R2 cutover time (residual; see checkpoint §6) |

## Repositories (V4 stable scope)

| Repo | Role | Branch | HEAD at V4 stable |
|------|------|--------|--------------------|
| `arumihsnek/hermes-chatgpt-mcp` | V4 connector / MCP control plane | `v4-candidate-integration` | `4ae5060931a64741185c5c8deb3886a5901f21cc` |
| `arumihsnek/hermes-chatgpt-mcp` | Phase-S source bundle | `release/source-bundle-phase-s` | `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` |
| `arumihsnek/hermes-chatgpt-mcp` | V4 control-plane docs (canonical) | `docs/v4-control-plane-source-of-truth-final` | `76cde68cba050873c4608a4385442249f4ff919f` (pre-truth-sync) — **this truth-sync lands via a new branch + PR** |
| `arumihsnek/hermes-agent` (implied) | Hermes Core baseline | `v4/baseline-post-update-885e9ef` (header) | `885e9ef73829` (header short) — **durable binding** |

## Public origin

| Surface | URL | Identity (live readback) |
|---------|-----|----------------------------|
| Public MCP | `https://kanban.hermesinthenight.duckdns.org/mcp` | `4ae5060931a6` / `beta` / `v4.wave0` |
| Public healthz | `https://kanban.hermesinthenight.duckdns.org/healthz` | `4ae5060931a6` / `beta` / `v4.wave0` |
| OAuth discovery | `https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-authorization-server` | standard DCR + PKCE S256 |
| OAuth protected-resource | `https://kanban.hermesinthenight.duckdns.org/.well-known/oauth-protected-resource` | resource metadata, scope list |

## Deployment topology (V4 stable runtime)

| Surface | Loopback | Process | Working dir | Public route | Identity |
|---------|----------|---------|-------------|---------------|----------|
| Stable (public) | `127.0.0.1:8789` | `hermes-chatgpt-mcp.service` (MainPID 2505228) | `/opt/hermes-chatgpt-mcp-canary` (override-redirected) | OpenResty `hermes-chatgpt-mcp.locations` (SHA-256 `27caf874…0816`, unchanged) | `4ae5060931a6` / `beta` / `v4.wave0` |
| Canary (isolated) | `127.0.0.1:8792` | `hermes-chatgpt-mcp-canary.service` (MainPID 2506251) | `/opt/hermes-chatgpt-mcp-canary` | none (systemd disabled; no public route) | `4ae5060931a6` / `beta` / `v4.wave0` |
| Pre-V4 `8791` beta | **not running** | `hermes-chatgpt-mcp-beta.service` (dormant) | n/a | n/a (pre-V4 v0.4 topology; not part of V4 stable) | n/a |

See [CHECKPOINT-2026-08-27-V4-STABLE.md](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) §3 for the full topology narrative (why 8789 is running the canary venv+WD, why 8791 is dormant, and what that means for operators).

## Rollback path (executable, byte-anchored, no installer run)

The V4 stable rollback is **three reversible mutations only**:

1. **Delete the override drop-in** at `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` (SHA-256 `d8d87c59…1d90a`).
2. **Restore the prior-good `build.json`** from the in-place backup `/var/lib/hermes-chatgpt-mcp/build.json.pre-surface-rectification-20260826T103951Z.bak` (commit `d7eba25ea8f6`, surface `stable`, deployed_at `2026-08-25T15:13:56Z`).
3. **One bounded `systemctl restart hermes-chatgpt-mcp.service`**.

No installer run, no wheel re-hash, no OAuth state rewrite, no credential rotation, no OpenResty mutation, no schema migration. See [CHECKPOINT-2026-08-27-V4-STABLE.md](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) §4 for the full rollback narrative, including the byte-anchored R2 manifest pins.

## Known residuals (documented, non-blocking)

| # | Residual | Severity | Source |
|---|----------|----------|--------|
| 1 | F-DOGFOOD-01 `bounded_log` cursor `BACKEND_ERROR` (additive convenience only) | LOW, fail-closed | `t_45647dc7` extended dogfood |
| 2 | W0 Low `initialize` 1999-01-01 negotiates 2025-11-25 | LOW | `t_068740be` independent review |
| 3 | Ephemeral worker venv `hermes_cli` `ModuleNotFoundError` (canary venv only) | LOW | canary-side observation |
| 4 | `deployed_at` reports canary's original deploy time, not 2026-08-27 cutover time | Informational | `t_a47fd88f` POST_SWITCH_REPORT |
| 5 | No `/opt/hermes-chatgpt-mcp` (stable checkout dir); rollback uses venv only | Informational | `t_1e84eb11` parent handoff |
| 6 | Pre-V4 `hermes-chatgpt-mcp-beta.service` (8791) dormant in V4 stable topology | Informational | live readback (no process on 8791) |

See [CHECKPOINT-2026-08-27-V4-STABLE.md](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) §6 for the full residual register and how each is bounded.

## Pre-flight invariants (parent `t_1e84eb11` ACCEPT chain, re-verified)

All 8 prerequisites PASS independently:

1. Clean build reproducible (`t_da03fbe7` 221/221) ✅
2. Canary deploy isolated (`t_56187ec4`, 8792 systemd disabled) ✅
3. Real MCP E2E (`t_5a9c43f7` 77/77 PASS) ✅
4. Wave 0-4 carry-forward (W0 13/13, W1 13/13, W2 20/20, W3 15/15, W4 15/15, integration 221/221) ✅
5. Extended dogfood (`t_45647dc7` 88/1, F-DOGFOOD-01 LOW non-blocking) ✅
6. Incident attestation (`t_ae8e6c64` NONE) ✅
7. Human gates (G2 `t_5b1757e2` YES, G3 `t_bae2e48b` YES, R3B `t_35a9e6b0` YES, all on exact 4ae5060) ✅
8. Traffic switch (`t_5a7cf41c` state verified under R3B; immutable public routing preserved) ✅

## Post-cutover evidence (durable, all post-2026-08-26T14:34:00Z)

- `t_5a7cf41c` (TRAFFIC-SWITCH-V4-STABLE) — promotion manifest sha256 `e5ffbf2c…94ba1`; immutable public routing preserved.
- `t_a47fd88f` (POST-SWITCH-SMOKE) — 23/23 contract checks through public origin, including healthz, OAuth PKCE end-to-end, MCP `initialize` 200, `tools/list` 71 (historical measurement at that timestamp; the reproducible count today against the same `4ae5060` is 66 — see [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md)) with all 6 v4.wave0 required tools present, board-read, one safe mutation (`t_c67c7d03`, comment_id 1337), and rollback predicate anchored.
- `t_f30cf660` (V4-CHATGPT-TOOL-PARITY-P0) — 2026-08-28 parity investigation that re-derived the raw `tools/list` count as **66** (from 71) and confirmed the **11**-tool ChatGPT contract is reachable via the live connector in the exact ChatGPT-style sequence. The reconciliation lives in [CHECKPOINT-2026-08-27-V4-STABLE.md §5.1](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) and the full report at `/home/ubuntu/.hermes/kanban/boards/hermes-chatgpt-mcp/attachments/t_f30cf660/REPORT.md`.
- `t_01200e57` (CHATGPT-SESSION-COMPAT-CONTRACT) — the frozen 11-tool ChatGPT contract that defines the ChatGPT-visible / invocable surface; **not** equal to raw `tools/list`. The V4.1-Compat-Plus expansion (`t_f30cf660` §6, 11 → 22) is held behind a separate, fresh Human Gate and is **not** in the V4 stable contract.
- `t_a343fc54` (V4-DOGFOOD-RETEST-01-ATTESTATION) — bounded chain DIAGNOSE→FIX→REVIEW→REGRESSION→RETEST closed; F-DOGFOOD-01 retained as documented non-blocking residual.
- `t_1e84eb11` (parent V4 stable ACCEPT) — this task's grandparent; all 8 prerequisites above PASS; live state verified.

## Related documents

- [CHECKPOINT-2026-08-27-V4-STABLE.md](docs/v4/CHECKPOINT-2026-08-27-V4-STABLE.md) — full truth-sync checkpoint (read this first).
- [CURRENT_STATE.md](docs/v4/CURRENT_STATE.md) — canonical source of truth, with new §17: 2026-08-27 V4 stable reconciliation.
- [EVIDENCE_AND_OPEN_QUESTIONS.md](docs/v4/EVIDENCE_AND_OPEN_QUESTIONS.md) — `Exact deployed connector SHA` removed from `STILL_NOT_PROVEN`; now resolved to `4ae5060931a6`.
- [DAG-SOFT-RETIRE-CONTRACT.md](docs/v4/DAG-SOFT-RETIRE-CONTRACT.md) — soft-retire discipline; `4ae5060` is edge_state-aware, so `PROJECTION_RUNTIME_P0` blocker is closed.
- [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](docs/v4/CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md) — source-precedence ladder + cold-start protocol (this release lives within that ladder).
- [TOOL_CATALOG.md](docs/v4/TOOL_CATALOG.md) + [v4-tool-catalog.json](docs/v4/v4-tool-catalog.json) — 79-entry catalog, updated metadata block.
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) + [SECURITY.md](docs/SECURITY.md) — v0.4 `8791` topology labelled **RETAIN / LINK; SUPERSEDE for current runtime**; new `## V4 stable runtime (2026-08-27)` section points at this release anchor.
- [STALE_DOCS.md](docs/v4/STALE_DOCS.md) — v0.4 `8791` topology descriptions explicitly classified as not-current-runtime.

## Authorship / review chain

| Step | Card | Profile | Status |
|------|------|---------|--------|
| Truth-sync authorship | `t_ca2ba9ae` (initial truth-sync) + `t_d1b356f4` (tool-count erratum 2026-08-28) | github-steward | running |
| Independent truth-sync audit | _open_ | reviewer | pending — proposed via PR |
| Canonical docs PR | _open_ | github-steward | proposed branch `docs/v4-post-v4-stable-truth-sync`; PR against `docs/v4-control-plane-source-of-truth-final` |
| Parity investigation (parent of the tool-count erratum) | `t_f30cf660` ACCEPT 2026-08-28 | investigator | DONE (66 raw / 11 ChatGPT / 71 historical) |
| ChatGPT session-compat contract (grandparent) | `t_01200e57` | investigator | DONE (11-tool frozen) |
| Post-switch smoke (historical 71) | `t_a47fd88f` ACCEPT 2026-08-27 | investigator | DONE |
| Parent ACCEPT | `t_1e84eb11` | operator | DONE 2026-08-27 (release identity pinned) |

The V4 stable is **NOT** a "go-merge" artifact; it is a **durable record** that any future V4.x cutover, audit, or external communication can cite without re-deriving the live state. Every claim in this document is bound to a SHA, a URL, a manifest pin, or a Kanban task id, and is independently re-verifiable.
