# ADR-001 · V4 Wave 0 Contract/Foundation

Status: ACCEPTED · 2026-08-25
Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92 (CUT3 t_765c4305)
Worktree: wt/t_261a7674 @ d7eba25 (dirty auth.py excluded from baseline per V4-BASELINE.md §1.2)
Deciders: software-architect (t_261a7674), reviewer t_b8410d63 (pending)
Branch isolation: dedicated V4 worktree/branch only; no mutation of v4/baseline-post-update-885e9ef or main.

## Context and evidence
- Frozen baseline pins: hermes-agent 885e9ef7 (dispatch edge_state), MCP d7eba25 (active-edge-only get_dispatch fallback), Phase-S ef22 (stable plane reference). Verified via `git cat-file -p HEAD` and build.json sha 986a4ffe… / wheel 757b25e… (V4-BASELINE.md §1).
- Single-MCP/control-plane topology adopted in docs/v4 MCP_TOPOLOGY_ADR (single server, internally privilege-separated adapters). Preserve.
- Observed current surface diverged from baseline docs: repo at t_261a7674 exposes canvas-style toolsets (map, code, global board ops); beta surface in docs expects 11-tool ChatGPT compat mode. Treat docs as intent, live as truth; compatibility layer must version.
- Gaps from KANBAN-READY-INTEGRITY-P1-2 still open at 885 (assignee_unresolvable, create/promote gates) — Wave 0 closes no gap silently; it adds provenance/introspection to make gaps observable.

## Decision drivers and invariants
- Drivers: auditable provenance before mutation; auth introspection must be explicit and fail-closed; schema/tool evolution must be versioned; release/canary must be rehearsable without promotion; dogfood must run on disposable fixtures.
- Invariants: single MCP process; read is global, write is per-grant one-board; OAuth scopes require hermes:read; board slugs canonical via ReadOnlyHermesStore.validate_board_slug; legacy default DB not exposed.

## Decision
Wave 0 ships as a thin contract layer on top of baseline without behavior change to canonical Hermes:

1. **Provenance** — `hermes_chatgpt_mcp/provenance.py` + `release.py` expose `V4Baseline` frozen pins and `CandidateProvenance` (candidate SHA, baseline SHA, build.json). `/healthz` always returns `build` (stable nulls when no manifest, beta exact), and adds `X-V4-Provenance: <candidate>/<baseline>/<surface>` response header. Manifest loader remains strict (BuildMetadataError) and public_dict stays minimal (3 fields).
2. **Auth/introspection contract** — `hermes_chatgpt_mcp/auth.py` policy unchanged; new read-only `get_introspection` helper surfaces granted scopes + board claim without leaking tokens. No scope widening; board claim derivation via verified_claims. Added explicit `AuthIntrospection` schema (versioned).
3. **Schemas and versioning** — `hermes_chatgpt_mcp/schemas.py` adds `ApiVersion = "v4.wave0"` and `ProvenanceHeader`/`AuthIntrospection` models with `extra=forbid` and `X-API-Version: v4.wave0` echo. No breaking field rename.
4. **Tool risk/scope boundaries** — `docs/v4-wave0/TOOL_RISK_BOUNDARIES.md` codifies MATRIX (read/create/manage/board:create/admin) and `server.py` annotates every tool with ToolAnnotations (readOnly/destructive/idempotent/openWorld). ChatGPT compat 11-tool allowlist retained.
5. **Dogfood harness** — `scripts/v4_dogfood_wave0.py` deterministic harness: disposable hermes-chatgpt-e2e-* fixtures only, provenance readback, stale/missing manifest negative, capability/readback mismatch, scope widening attempt, unsupported schema version. Produces PASS/FAIL JSON, no project-board mutation.
6. **Release/canary primitives** — `scripts/verify_beta_release.py` remains verifier; `release.py` adds `canary_manifest()` helper to generate/validate canary build.json detached from live state. No live promotion in Wave 0.

## Considered alternatives
- A: Single-MCP contract layer (chosen) — reversible, incremental, reuses ReadOnlyHermesStore/mode=ro + query_only=ON.
- B: Split MCP by privilege (read/write/admin processes) — rejected: latency, session re-establishment, ChatGPT single-connector limit, minimal security gain vs adapter isolation.
- C: Event-sourced provenance log — rejected for Wave 0: overkill; append-only audit deferred to later wave; V4 baseline is CRUD+hermes_cli.kanban_db.create_task.

## Consequences and accepted risks
- Positive: every Wave 0 change is provenance-tagged; auth decisions introspectable; tool surface versioned; harness/canary rehearsable offline.
- Negative: extra header/version adds 1 RTT header; stable /healthz now exposes build=nulls (intentional, no leak).
- Risks: dirty auth.py residue explicitly unported; any future auth port must diff vs d7eba25, not stash replay. Unknown assignee gap still open — now observable via introspection/diagnostics but not fixed here.

## Data/event/provenance/correction contracts
- Canonical: hermes-agent 885 tree f39aa06, MCP d7eba25 tree 427a7ee, build.json sha 986a…, wheel 757b25e… (§1 pins). All Wave 0 files carry header `Baseline: v4/baseline-post-update-885e9ef/... Candidate: wt/t_261a7674/d7eba25+`.
- Provenance: BuildMetadata.public_dict() is projection; corrections via new manifest, never silent history rewrite.
- Corrections: manifest mismatch ⇒ fail-closed BuildMetadataError; scope/board mismatch ⇒ SCOPE_REQUIRED/BOARD_SESSION_MISMATCH; tool strict extra=forbid.

## Rollout and verification
- Rollout: worktree-only; no systemd/OpenResty change; no live promotion. Staged: (1) commit on wt/t_261a7674, (2) pytest -q (199+ expected), (3) harness dry-run in /tmp e2e board, (4) review t_b8410d63.
- Verification: `pytest -q`, `python -m compileall`, targeted `test_healthz_includes_public_beta_build_metadata`, negative manifest test, harness JSON output. Unrun checks labeled UNVERIFIED.
- Backwards compatibility: Add-only. Stable clients ignoring X-V4-Provenance/X-API-Version remain valid. Manifest absent ⇒ empty provenance (existing behavior). Rollback: revert wt/t_261a7674 commits; stable health returns to prior (beta-only build). No DB migration.

## Rebuild and rollback
- Rebuild: `git archive HEAD` → wheel → pip install --no-deps; build.json regeneration via release.canary_manifest().
- Rollback targets: hermes-agent parent 165d1849, MCP prior wheel 56b7b7f…, build.json.bak per V4-BASELINE.md §5. Restores are `pip install --force-reinstall <wheel>` + service restart (max 2).

## Follow-ups and review date
- Review t_b8410d63 must verify provenance readback, header parity, strict schemas, scope fail-closed. Next wave (profiles/skills) depends on J0 join after W0 REVIEW PASS.
