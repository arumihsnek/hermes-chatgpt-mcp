# V4 Stable Acceptance — Documentation Truth-Sync Checkpoint — 2026-08-27

**Status:** POST-V4 STABLE TRUTH-SYNC (supplemental to the canonical 2026-08-19 V4 design + 2026-08-21, 2026-08-24, 2026-08-25 reconciliations)
**Reconciliation date:** 2026-08-27 (UTC)
**Authored by:** github-steward (task `t_ca2ba9ae`)
**Companion review card:** _open_ — independent truth-sync audit; this checkpoint is **proposed** for `docs/v4-control-plane-source-of-truth-final` via a new branch + PR; not yet merged.
**Scope of this document:** Sync `docs/v4` to the **actually accepted V4 stable** (not historical branches or candidate assumptions). Update the architecture / contracts / tool catalog / runbooks / release docs with the exact stable Connector/Core SHAs and bundle IDs, schema/tool-surface version, deployment topology, rollback path, known residuals, and dogfood lessons. Remove stale claims **only with evidence**; preserve historical context.

> **Cold-start rule (carried from [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)):** live runtime readback > live Kanban/runs/events > fresh SHA-bound evidence > current Git HEAD > current checkpoints > current repo docs > historical cards. This checkpoint is **rank 5** in that ladder; live readback is always allowed to override it.

---

## 0. Why this checkpoint exists

The previous `docs/v4` reconciliations (2026-08-19 canonical design + 2026-08-21 release-candidate + 2026-08-24 recovery + 2026-08-25 freshness) all pre-date the V4 stable acceptance. They all carry:

- `Documentation base: 9900c10` (pre-V4 beta worktree, **not the V4 candidate**)
- `Deployed connector SHA: STILL_NOT_PROVEN`
- `Kanban_Beta` as stale naming metadata
- `Hermes Version: 0.20.2`
- `Source HEAD: 39cfd1ab41` (pre-V4)
- `live_mcp_discovery_tools: 54` (2026-08-19 discovery)

After the V4 stable acceptance (parent `t_1e84eb11` ACCEPT 2026-08-27), the **authoritative truth** has shifted. The V4 stable is now:

| Identity (V4 stable, accepted) | Value |
|-------------------------------|-------|
| Connector (V4 stable commit) | `4ae5060931a64741185c5c8deb3886a5901f21cc` (short `4ae5060`) |
| Connector branch | `v4-candidate-integration` |
| Connector commit message | `fix(integration): resolve cross-wave residuals — board-scoped attachments (FS drift) + cursor paging wired (Wave-2 F1)` |
| Connector commit date | 2026-08-26T14:01:53Z |
| Phase-S source bundle (MCP repo, `release/source-bundle-phase-s`) | `9a8410b4e883e27a4e0572951ee00f9faf4f3d19` (short `9a8410b4`) |
| Hermes Core MCP baseline (header) | `d7eba25ea8f6` (full `d7eba25ea8f692d2d0b65d7e5044df79e94c8a92`) |
| Hermes Core baseline branch (header) | `v4/baseline-post-update-885e9ef` (short `885e9ef73829`) |
| Phase-S short SHA (parent handoff) | `ef22b89e8b49` |
| Surface (build.json + x-v4-provenance) | `beta` (controller classifies the deployment as STABLE; `Kanban_Beta` discovery label is stale naming metadata) |
| API version (x-api-version) | `v4.wave0` |
| Live V4 provenance header | `4ae5060931a6/d7eba25/beta` |
| Live tool count (MCP `tools/list`, post-switch smoke `t_a47fd88f`) | **71** (vs the 2026-08-19 54-tool discovery) |
| v4.wave0 required tools (all 6 present) | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` |
| Public MCP origin | `https://kanban.hermesinthenight.duckdns.org/mcp` |
| Stable loopback | `127.0.0.1:8789` (override-redirected to canary venv+WD, see §3) |
| Canary loopback (isolated, no public route) | `127.0.0.1:8792` (same `4ae5060` image) |
| Pre-V4 beta service (`hermes-chatgpt-mcp-beta.service`, port 8791) | **not running** in the V4 stable topology; superseded by the 4ae5060 canary + 8789 override (see §3) |
| Deployed-at (build.json) | `2026-08-26T14:34:00Z` — **residual note:** this is the canary's original deploy time, **not** the stable cutover time; the 2026-08-27 R2 cutover did **not** update `deployed_at` (documented as non-contract residual) |

The V4 stable identity is **NOT_PROVEN-PROMOTION-SAFE** to cite as current. Previous docs MUST be updated to point at these SHAs, not at `9900c10` / `39cfd1ab41` / `STILL_NOT_PROVEN`.

---

## 1. Live readback evidence (captured at reconciliation time)

All three live surfaces were re-read at reconciliation time and produced **identical** identity headers. SHA-256 of the manifest files are byte-anchored to the parent `t_1e84eb11` R2 manifest; all four pins match exactly.

### 1a. healthz (loopback + public + canary)

| Surface | URL | `x-v4-provenance` | `x-api-version` | `x-baseline-branch` | `x-baseline-mcp` | `build_commit` | `surface` | `deployed_at` |
|---------|-----|-------------------|-----------------|---------------------|------------------|----------------|-----------|----------------|
| Stable loopback | `http://127.0.0.1:8789/healthz` | `4ae5060931a6/d7eba25/beta` | `v4.wave0` | `v4/baseline-post-update-885e9ef` | `d7eba25ea8f6` | `4ae5060931a64741185c5c8deb3886a5901f21cc` | `beta` | `2026-08-26T14:34:00Z` |
| Public origin | `https://kanban.hermesinthenight.duckdns.org/healthz` | `4ae5060931a6/d7eba25/beta` | `v4.wave0` | `v4/baseline-post-update-885e9ef` | `d7eba25ea8f6` | `4ae5060931a64741185c5c8deb3886a5901f21cc` | `beta` | `2026-08-26T14:34:00Z` |
| Canary loopback | `http://127.0.0.1:8792/healthz` | `4ae5060931a6/d7eba25/beta` | `v4.wave0` | `v4/baseline-post-update-885e9ef` | `d7eba25ea8f6` | `4ae5060931a64741185c5c8deb3886a5901f21cc` | `beta` | `2026-08-26T14:34:00Z` |

**Match:** all three surfaces report the same V4 stable identity. The OpenResty public route is the 8789 stable (override-redirected to canary venv+WD); the 8792 canary is the same image, isolated, no public route.

### 1b. On-disk manifest pins (SHA-256)

| File | Path | SHA-256 (this run) | R2 manifest pin | Match |
|------|------|---------------------|------------------|-------|
| `build.json` | `/var/lib/hermes-chatgpt-mcp/build.json` | `b83efaea3d253074f546661da4f27cfc0b4a579adad3d0f45fc48f2f0e2a231e` | `b83efaea…231e` (full) | ✅ |
| `override.conf` | `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` | `d8d87c59817cfce591fd0a9bfcd54898534f84c96d1d461e1fbf8ffed8d1d90a` | `d8d87c59…1d90a` (full) | ✅ |
| `hermes-subdomains.conf` | `/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-subdomains.conf` | `b9d2daa9b5a420db2142f9ef2644ba4d9e239d5b4b959fca0bd5e0c0f5ae187b` | `b9d2daa9…187b` (full, unchanged) | ✅ |
| `hermes-chatgpt-mcp.locations` | `/opt/1panel/apps/openresty/openresty/conf/conf.d/hermes-chatgpt-mcp.locations` | `27caf8746d8eb44b18492c48f041bfd0c90a2f965749bae246e6d824efb0c816` | `27caf874…0816` (full, unchanged) | ✅ |

**No OpenResty mutation in the R2 cutover; no credential change; no schema migration.** The override.conf is the only behavioral redirection; its content is documented in §3.

### 1c. Pre-promotion backups (preserved in-place)

These three files are the on-disk evidence that the V4 stable is **recoverable** to the prior-known-good state, **without an installer run**:

| Backup | Content | Last good before V4 stable |
|--------|---------|-----------------------------|
| `/var/lib/hermes-chatgpt-mcp/build.json.pre-surface-rectification-20260826T103951Z.bak` | `{"build_commit": "d7eba25ea8f692d2d0b65d7e5044df79e94c8a92", "deployed_at": "2026-08-25T15:13:56.886640+00:00", "surface": "stable"}` | 2026-08-25 15:13 UTC (pre-4ae5060, surface-rectification generation) |
| `/var/lib/hermes-chatgpt-mcp/build.json.pre-edge-state-20260825T1440Z.bak` | `{"build_commit": "dc25e8bf7a66be87e12da33613d83c874be50038", "deployed_at": "2026-08-24T19:35:56.489600Z", "surface": "stable"}` | 2026-08-24 19:35 UTC (recovery-mutation generation) |
| Stable venv (`/opt/venvs/hermes-chatgpt-mcp`) | Pre-promotion venv, mtime 2026-08-17 | Pre-V4-candidate; **NOT** the runtime that 8789 currently serves (see §3) |

> These backups are the byte-anchored "prior-good" targets. They are NOT the V4 stable. They are listed here **only** as the rollback path evidence (see §4).

---

## 2. Pre-flight invariants (must hold before any of the changes below are applied)

These are the same eight prerequisites as the parent `t_1e84eb11` ACCEPT, re-verified this run from the live readback above:

| # | Prerequisite | Source / evidence | This-run verification |
|---|--------------|-------------------|------------------------|
| 1 | Clean build reproducible | `t_da03fbe7` 221/221 in fresh `/tmp/hermes-v4-build` py3.11.15 | `build_commit=4ae5060931a6` matches clean-build HEAD ✅ |
| 2 | Canary deploy isolated | `t_56187ec4` 8792 systemd disabled, full isolation matrix | `MainPID 2506251` on 127.0.0.1:8792, system unit disabled per parent handoff ✅ |
| 3 | Real MCP E2E | `t_5a9c43f7` 77/77 PASS OAuth/DCR PKCE S256 + refresh rotation + board-scoped grants + dispatch realism on `hermes-chatgpt-e2e-04780a62` | Same OAuth DCR live; tools/list 71 with all 6 v4.wave0 required tools ✅ |
| 4 | Wave 0-4 carry-forward | W0 13/13, W1 13/13, W2 20/20, W3 15/15, W4 15/15, integration 221/221 (`t_068740be` + `t_f96589bf`) | `4ae5060` is the integrated candidate head ✅ |
| 5 | Extended dogfood | `t_45647dc7` 88/1 with F-DOGFOOD-01 LOW non-blocking; full DIAGNOSE→FIX→REVIEW→REGRESSION→RETEST chain closed | F-DOGFOOD-01 retained as documented non-blocking residual (see §6) ✅ |
| 6 | Incident attestation | `t_ae8e6c64` NONE — zero release-blocking incidents; full chain `t_7afc509f`→`t_a0d6bae7`→`t_ed301a4c`→`t_aad72b38`→`t_a343fc54` all done | No open release-blocker incidents ✅ |
| 7 | Human gates | G2 `t_5b1757e2` YES (4ae5060, R2 manifest, `9d051d19` nonce) + G3 `t_bae2e48b` YES (`4745f2cd` manifest, `b51d1f91` nonce) + R3B `t_35a9e6b0` YES (continue from applied state, scope-limited) | All three gates YES on exact 4ae5060 ✅ |
| 8 | Traffic switch | `t_5a7cf41c` state verified under R3B; promotion manifest sha256 `e5ffbf2c…94ba1`; immutable public routing preserved | 8789 → public origin → 4ae5060 ✅ |

> **Result:** all 8 prerequisites PASS independently. The V4 stable identity is durable; the prior `STILL_NOT_PROVEN` claim is now **RESOLVED** for the deployed connector SHA. Other `NOT_PROVEN` items (live HTTP auth surface for native API, dynamic tool registration, etc.) remain explicitly unresolved (see [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) and §6 below).

---

## 3. Post-V4-stable deployment topology (vs the pre-V4 doc baseline)

This section corrects `docs/DEPLOYMENT.md` and `docs/SECURITY.md`, which were authored before V4 stable and describe the **v0.4** `8789 stable / 8791 beta` topology.

### 3a. Current live topology (this run, 2026-08-27 21:31 UTC)

| Surface | URL / port | Systemd unit | Interpreter | Working dir | Public route | Identity (live readback) |
|---------|-----------|--------------|-------------|-------------|---------------|----------------------------|
| Stable (public) | `https://kanban.hermesinthenight.duckdns.org` → `127.0.0.1:8789` | `hermes-chatgpt-mcp.service` (MainPID 2505228) | `/opt/venvs/hermes-chatgpt-mcp-canary/bin/python` (override-redirected) | `/opt/hermes-chatgpt-mcp-canary` (override-redirected) | OpenResty `hermes-chatgpt-mcp.locations` (SHA-256 `27caf874…0816`, unchanged) | `4ae5060931a6` / `beta` / `v4.wave0` |
| Canary (isolated) | `127.0.0.1:8792` | `hermes-chatgpt-mcp-canary.service` (MainPID 2506251) | `/opt/venvs/hermes-chatgpt-mcp-canary/bin/python` | `/opt/hermes-chatgpt-mcp-canary` | none — systemd disabled, no public route | `4ae5060931a6` / `beta` / `v4.wave0` |
| Pre-V4 beta (`hermes-chatgpt-mcp-beta.service`, port 8791) | **not running** | not started in the V4 stable topology | n/a | n/a | none | n/a — see residual note in §6 |

### 3b. Why 8789 is running the canary venv+WD (and what that means)

`/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` (SHA-256 `d8d87c59…1d90a`) declares:

```ini
[Service]
# Promote stable 8789 service to candidate 4ae5060931a64741185c5c8deb3886a5901f21cc.
# Swaps only the interpreter + WorkingDirectory; unit file, env, state paths, and port 8789 preserved.
Environment=HERMES_KANBAN_BOARD=hermes-chatgpt-mcp
ExecStart=
ExecStart=/opt/venvs/hermes-chatgpt-mcp-canary/bin/python -m hermes_chatgpt_mcp.server
WorkingDirectory=/opt/hermes-chatgpt-mcp-canary
```

This is the **only** behavioral redirection in the V4 stable. The systemd **unit file, env, state paths, and port 8789 are preserved**. OpenResty still terminates TLS and forwards only the canonical MCP/OAuth/health paths to 8789. The override is the smallest possible deviation from the pre-promotion state and is the **only** item the rollback path needs to revert (see §4).

> **Note for future operators:** the per-service env file `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` retains the pre-promotion `MCP_SURFACE=beta` value, but its mtime is **2026-08-18** (pre-promotion) and it was **not** touched by the V4 stable cutover. The `surface=beta` in the current `build.json` is the canary's own build metadata, not driven from the env file. This is a **residual**, not a contract violation.

### 3c. Why the pre-V4 `8791` beta is not part of the V4 stable topology

The pre-V4 `hermes-chatgpt-mcp-beta.service` (port 8791, `kanban-beta.hermesinthenight.duckdns.org`) is **not running**. The V4 wave0 / Phase-S / R2 promotion strategy chose a **canary + override** model (one candidate image at `4ae5060`, served both at 8792 isolated and at 8789 via override) rather than a parallel stable/beta dual-deployment. The `8791` pre-V4 beta deployment unit and its `/var/lib/hermes-chatgpt-mcp-beta` state directory still exist on disk but are **not part of the V4 stable runtime**. They may be **resurrected** for a future V4.x parallel deployment (or for `v4-candidate-integration` pre-stable dogfood), but doing so requires a fresh authorization and is **out of scope** for the V4 stable.

`docs/DEPLOYMENT.md` and `docs/SECURITY.md` still describe the v0.4 `8791` topology and must be **updated** to point at the current V4 stable topology above. The v0.4 `8791` descriptions are preserved as **dated v0.4 contract** in [STALE_DOCS.md](STALE_DOCS.md); they are no longer current runtime truth.

---

## 4. Rollback path (executable, byte-anchored, no installer run)

The V4 stable rollback is **three reversible mutations only**; the same three items the parent `t_1e84eb11` enumerated. All targets are on this host, in-place, and do **not** require an installer run, a wheel re-hash, an OAuth state rewrite, a credential rotation, an OpenResty mutation, or a schema migration.

| Step | File | Action | Pre-state (this run) | Post-state | Notes |
|------|------|--------|----------------------|-------------|-------|
| 1 | `/etc/systemd/system/hermes-chatgpt-mcp.service.d/override.conf` | **Delete the override drop-in** (`rmdir` if no other drop-ins; otherwise `rm override.conf`) | SHA-256 `d8d87c59…1d90a` (override-redirect to canary venv+WD) | systemd reads the base unit: interpreter = `/opt/venvs/hermes-chatgpt-mcp/bin/python`, WD = `/var/lib/hermes-chatgpt-mcp` (pre-promotion default), port 8789 preserved | The pre-promotion interpreter and WD come from the base unit file; the env file `/home/ubuntu/.hermes/hermes-chatgpt-mcp.env` is unchanged (mtime 2026-08-18). |
| 2 | `/var/lib/hermes-chatgpt-mcp/build.json` | **Restore the prior-good backup** `build.json.pre-surface-rectification-20260826T103951Z.bak` over the current `build.json` | current content: `{"build_commit":"4ae5060931a64741185c5c8deb3886a5901f21cc","surface":"beta","deployed_at":"2026-08-26T14:34:00Z"}` (SHA-256 `b83efaea…231e`) | `{"build_commit": "d7eba25ea8f692d2d0b65d7e5044df79e94c8a92", "deployed_at": "2026-08-25T15:13:56.886640+00:00", "surface": "stable"}` (the surface-rectification prior-good) | The R2 manifest pins the **pre-state byte** of `build.json`; the `surface-rectification` backup is the immediate prior-good, NOT the `dc25e8bf` recovery-mutation generation (which is the prior-before-the-prior). |
| 3 | `hermes-chatgpt-mcp.service` | **One bounded `systemctl restart hermes-chatgpt-mcp.service`** (the only restart; no daemon-reload, no OpenResty reload) | MainPID 2505228 (canary venv+WD) | MainPID = new pid running the pre-promotion venv+WD on port 8789 | OpenResty is **not** reloaded; `hermes-subdomains.conf` and `hermes-chatgpt-mcp.locations` SHA-256 are unchanged across the V4 stable cutover, so they require no reload. |

**Why this is sufficient and what it does not require:**

- **No installer run.** The pre-promotion venv `/opt/venvs/hermes-chatgpt-mcp` is still on disk (mtime 2026-08-17); rollback reuses it directly.
- **No wheel re-hash.** The pre-promotion wheel SHA is implied by the pre-promotion venv contents and is not separately required to activate the venv.
- **No OAuth state rewrite.** `/var/lib/hermes-chatgpt-mcp/oauth-state.json` is **NOT** touched by the V4 stable cutover. Its mtime `2026-08-27T20:40:40Z` is in the recovery window (parent handoff), not the cutover window. Rolling back to the prior-good build.json does not invalidate any DCR client or refresh-grant record. If a future surface cutover mutates oauth-state.json, the rollback must **also** restore that mutation; this is not the case for the current V4 stable.
- **No credential rotation.** `MCP_OAUTH_SIGNING_KEY` in the env file is unchanged across the cutover.
- **No OpenResty mutation.** `hermes-subdomains.conf` and `hermes-chatgpt-mcp.locations` SHA-256 are byte-identical pre- and post-cutover (verified this run).
- **No schema migration.** The V4 stable is a code cutover only; the canonical board databases (`.hermes/kanban/boards/*/tasks.db`) are untouched.

**Optional cleanup (post-rollback, non-blocking):** the 8792 canary is independent. It may be left running for diagnostic reuse, or stopped with `systemctl stop hermes-chatgpt-mcp-canary.service`. Stopping the canary does not affect 8789.

**Rollback risk acknowledgment:** a rollback to the pre-V4-stable state means the prior-good identity (`d7eba25ea8f6`, surface=`stable`, no `v4.wave0` headers) returns to public. The MCP `tools/list` returns the pre-V4 surface (54 tools, no `get_dispatch`/`get_task_graph` improvements, no `bound_log` cursor for `log` tool). The prior-good identity was the last identity that passed the full MCP E2E + dogfood chain under the v0.4 contract; it is **safe to roll back to** without re-validation.

---

## 5. Schema / tool-surface version — `v4.wave0`

The V4 stable exposes a **stable** tool-surface contract identified by the `x-api-version: v4.wave0` header on every MCP response.

| Field | Value | Source |
|-------|-------|--------|
| `x-api-version` (response header) | `v4.wave0` | live readback (this run, all 3 surfaces) |
| `x-v4-provenance` (response header) | `4ae5060931a6/d7eba25/beta` | live readback (this run) |
| `x-baseline-branch` (response header) | `v4/baseline-post-update-885e9ef` | live readback (this run) |
| `x-baseline-mcp` (response header) | `d7eba25ea8f6` | live readback (this run) |
| Live MCP `tools/list` tool count | **71** | `t_a47fd88f` post-switch smoke (23/23 contract checks, including tool-surface cardinality) |
| v4.wave0 required tools (all 6 present) | `list_boards`, `get_board`, `list_tasks`, `get_task`, `create_task`, `add_comment` | `t_a47fd88f` post-switch smoke, contract check #10 |
| Other notable Wave-0/1/2/3/4 features | board-scoped attachments (FS-drift fix, `4ae5060`); cursor paging for `list_tasks`/`runs` (Wave-2 F1); Wave-4 control-plane (provenance, human gates, canary, bounded status) | `4ae5060` commit message: `fix(integration): resolve cross-wave residuals — board-scoped attachments (FS drift) + cursor paging wired (Wave-2 F1)` |

> **Convention for future waves:** the `x-api-version` header is the **stable** API surface identifier. A future `v4.wave1` (or higher) becomes current **only** after its own full E2E + dogfood + Human Gate + promotion chain; until then, the surface remains `v4.wave0` and the `x-v4-provenance` advances to the new connector SHA. This convention is **not yet** enforced by the connector; the current contract is that the four headers are advisory and the build.json + service identity are the durable truth.

---

## 6. Known residuals (documented, non-blocking)

These residuals are **explicitly preserved** by the V4 stable acceptance. They are not blockers; they are accepted as documented limitations of the current V4 stable cutover.

| # | Residual | Severity | Source | Status |
|---|----------|----------|--------|--------|
| 1 | **F-DOGFOOD-01** `bounded_log` cursor `BACKEND_ERROR` — additive convenience only; `tail_bytes`, `get_activity`, `runtime_status`, `diagnostics` cover the observability acceptance | LOW, fail-closed | `t_45647dc7` extended dogfood (88/1) | **Retained** (not fixed in V4 stable) |
| 2 | **W0 Low** `initialize` 1999-01-01 negotiates 2025-11-25 — no security impact, carried from `t_068740be` | LOW | `t_068740be` independent review | **Retained** (not fixed in V4 stable) |
| 3 | **Ephemeral worker venv** `hermes_cli` `ModuleNotFoundError` — isolated to the canary venv, bounded non-leak, not reproduced in retest, does **not** affect stable 8789 | LOW | canary-side observation | **Retained** (canary venv only) |
| 4 | **`deployed_at` semantics** — `build.json` reports `2026-08-26T14:34:00Z` which is the canary's original deploy time, **not** the 2026-08-27 R2 cutover time | Informational | `t_1e84eb11` parent handoff; `t_a47fd88f` POST_SWITCH_REPORT residual | **Retained** (no contract violation; documented for downstream consumers) |
| 5 | **No `/opt/hermes-chatgpt-mcp` (stable checkout dir)** — stable venv exists at `/opt/venvs/hermes-chatgpt-mcp`; the corresponding checkout dir does not exist on this host; rollback uses the venv only | Informational | `t_1e84eb11` parent handoff | **Retained** (rollback path documented; no checkout needed) |
| 6 | **Pre-V4 `hermes-chatgpt-mcp-beta.service` (8791) not running** in the V4 stable topology; pre-V4 `8791` deployment unit and `/var/lib/hermes-chatgpt-mcp-beta` state dir still exist on disk | Informational | live readback (no process on 8791) | **Retained** (resurrection requires fresh authorization; out of scope for V4 stable) |
| 7 | **STILL_NOT_PROVEN** items in [EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md) §2 (other than the now-resolved "Exact deployed connector SHA"): live HTTP/API auth surface for native API, provider/model validity, dynamic tool registration, etc. | Various | unchanged from 2026-08-19 / 2026-08-21 | **Preserved** (each is unrelated to the V4 stable cutover) |

---

## 7. Dogfood lessons (carried into the V4 stable docs)

The 2026-08-25 DAG soft-retire / extended dogfood program produced lessons that this checkpoint and the V4 stable docs carry forward. None of these are blockers; they are constraints on how the V4 stable **can be evolved**.

1. **DAG `edge_state` soft-retire is canonical** (`active|retired|rebound`; retired/rebound carry zero gating power; provenance fields are historical evidence only). See [DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md). The V4 stable runtime `4ae5060` is **edge_state-aware** (the `PROJECTION_RUNTIME_P0` blocker from 2026-08-25 is closed by `4ae5060`). Future connector revisions MUST NOT delete retired edges or complete `barrier` for throughput; the soft-retire discipline is the durability guarantee.
2. **Disposable fixture boards only.** Mutating dogfood uses disposable `hermes-chatgpt-e2e-*` fixtures **only**; never the project board `hermes-chatgpt-mcp`. The V4 stable post-switch smoke `t_a47fd88f` is the only post-cutover write to the project board (one bounded `add_comment` on `t_c67c7d03`); all other writes during dogfood were on disposable boards.
3. **Live readback > discovery > docs.** A checked-out doc tree is **not** automatically truth. The V4 stable cutover is verified by **three independent live surfaces** (loopback 8789, public origin, canary 8792) reporting identical headers, **plus** four on-disk SHA-256 pins matching the R2 manifest. Any future V4.x cutover must do the same.
4. **Source Precedence Ladder** (carried from [CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)) is the **only** allowed override rule. A doc or card's age does not make it wrong within its scope, but it cannot outrank a live readback.
5. **Fail-closed on unknown identity.** The V4 stable cutover requires the canary handshake (`t_be036abf` style) to observe a fresh MCP/OAuth session + observed receipt (canary/release ID, Connector SHA, Core SHA/version, schema/tool-surface version, scopes actually granted/effective) before first mutation. A mismatch / unknown identity ⇒ FAIL. The V4 stable cutover met this requirement (parent `t_1e84eb11` evidence chain).
6. **Scope vocabulary is exact.** Current proven scopes are `hermes:read`, `hermes:create`, `hermes:manage`, `hermes:board:create`, `offline_access` (connection only). Finer proposed scopes in `CURRENT_STATE.md` §9 are **PROPOSED only**, **not current**; the V4 stable does **not** migrate to them. Any future fine-grained scope migration requires a fresh connector release and its own E2E + dogfood chain.
7. **Operator-authoritative discovery proves exposure only.** The V4 stable exposes **71 tools** (live `tools/list`); exposure is not validation. The 71-tool count is the **post-wave-0-to-4** count, not a contract. The 6 v4.wave0 required tools are the only tools that MUST be present in every V4 wave.

---

## 8. Cross-references (what to read in what order)

1. **[README.md](README.md)** — `docs/v4` index, updated to point at this checkpoint + `RELEASE-STABLE-V4.md`.
2. **[CURRENT_STATE.md](CURRENT_STATE.md)** — section 17 added: 2026-08-27 V4 stable reconciliation. `Deployed connector SHA` flipped from `STILL_NOT_PROVEN` to `4ae5060931a64741185c5c8deb3886a5901f21cc` (resolved). `Live MCP tool count` updated from 54 to 71.
3. **[TOOL_CATALOG.md](TOOL_CATALOG.md) + [v4-tool-catalog.json](v4-tool-catalog.json)** — metadata block updated: `deployed_connector_sha: 4ae5060931a6`, `live_discovery_tools: 71`, `hermes_version: 0.20.2 (2026.8.16) [unchanged, but reconciled against V4 stable]`, `last_reconciled: 2026-08-27`, `api_version: v4.wave0`.
4. **[EVIDENCE_AND_OPEN_QUESTIONS.md](EVIDENCE_AND_OPEN_QUESTIONS.md)** — `Exact deployed connector SHA` removed from `STILL_NOT_PROVEN` (now resolved). 4ae5060931a6 added as the durable binding. Known residuals in §6 above are recorded with cross-references.
5. **[DEPLOYMENT.md](../DEPLOYMENT.md) + [SECURITY.md](../SECURITY.md)** — v0.4 `8791` topology labelled **RETAIN / LINK; SUPERSEDE for current runtime**; new `## V4 stable runtime (2026-08-27)` section points at this checkpoint. STALE_DOCS.md already classifies the v0.4 descriptions correctly; the cross-link is now in place.
6. **[MCP_TOPOLOGY_ADR.md](MCP_TOPOLOGY_ADR.md) + [CONTROL_PLANE_SPEC.md](CONTROL_PLANE_SPEC.md)** — topology section updated to point at the post-V4-stable topology (`8789 / 8792 canary / 8791 dormant`) and the `v4.wave0` API surface.
7. **[STALE_DOCS.md](STALE_DOCS.md)** — `docs/SECURITY.md` and `docs/DEPLOYMENT.md` rows updated to flag the v0.4 `8791` topology descriptions as **not-current-runtime**; the v0.4 `8791` descriptions are retained as **dated v0.4 contract**.
8. **[DAG-SOFT-RETIRE-CONTRACT.md](DAG-SOFT-RETIRE-CONTRACT.md)** — unchanged; `4ae5060` is edge_state-aware, so the `PROJECTION_RUNTIME_P0` blocker is **closed** in the V4 stable.
9. **[CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md](CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md)** — unchanged as the source-precedence + cold-start protocol document; this checkpoint is **supplemental** and lives within its ladder.
10. **[RELEASE-STABLE-V4.md](../RELEASE-STABLE-V4.md)** — new top-level file: short release provenance summary for cross-document linking.

---

## 9. The proposed PR

This checkpoint is **proposed** for `docs/v4-control-plane-source-of-truth-final` (canonical docs branch, current head `76cde68cba05`). It does **not** mutate the canonical branch directly. The new branch `docs/v4-post-v4-stable-truth-sync` carries this checkpoint + the cross-referenced updates; a PR will be opened for independent review. No merge will be performed without separate, explicit, exact-revision authorization (the same discipline the parent `t_1e84eb11` Human Gate chain enforced).
