# G2 Conductor Checkpoint — 2026-08-25 Material Findings & Source-of-Truth Guardrails

**Status:** CANONICAL V4 DOCUMENTATION TRUTH-SYNC (supplemental to `CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md` and `DAG-SOFT-RETIRE-CONTRACT.md`)
**Authored by:** github-steward (task `t_1da73350`, DOGFOOD-CHECKPOINT-20260825-G2)
**Reconciliation date:** 2026-08-25 (UTC)
**Documentation base:** `2336acd` (local `wt/dogfood-ledger-20260825` ref; deployed connector SHA is **NOT_PROVEN**)
**Companion parent cards:** `t_f00c7f56` (PRINCIPAL-CONDUCTOR), `t_8fa8f4ff` (BEADS-SPIKE-5 decision package)
**Scope of this document:** Persist seven material conductor findings surfaced during the G2 Beads / V4 / Hermes-manage transition, link the exact task/run evidence for each, and record the source-precedence, fail-closed, and recovery/rebind rules that govern how those findings must be interpreted and acted on. **NO runtime mutation was performed by this card or any finding it records.** No deploy/restart/OAuth/DCR/cutover/PASS is claimed beyond the exact evidence cited.

---

## 0. Update precedence (carried from the current-truth ladder)

This file is **current repo docs** (rank 6 on the Source Precedence Ladder in `CHECKPOINT-2026-08-25-CURRENT-TRUTH-FRESHNESS.md`). It is superseded by:
1. Live runtime / service readback (rank 1)
2. Live canonical Kanban state — read from the exact owning board DB (rank 2)
3. Fresh immutable evidence bound to exact SHA / run id (rank 3)
4. Current Git HEAD / worktrees / refs (rank 4)

Every claim here is evidence-bound and dated. **Never infer graph truth — edge state, verdicts, statuses — from a task body alone.** Re-read the board and the exact run/event payloads before acting.

> **Board ownership note:** `hermes-chatgpt-mcp` (ChatGPT MCP connector board) and `hermes-v4-planning` (V4 release board) are **separate SQLite boards**. Tasks in this checkpoint may live on either board; the owning board is named per finding. The default `hermes kanban` CLI binding in this worker session resolved to a different board than `hermes-chatgpt-mcp`, so all edge/run/comment assertions here were re-verified by direct SQLite read of the owning board's `kanban.db`, not by a single CLI default.

---

## 1. Duplicate Beads review dispatch — G2 made sole authority, old review reclaimed/archived with provenance

**Finding:** Two independent Beads build-vs-adopt reviews ran concurrently — the historical predecessor `t_b65aff04` (BEADS-SPIKE-4) and the fresh G2 generation `t_3e8b3ba4` (BEADS-SPIKE-4-G2). A duplicate canonical verdict was prevented by making G2 the sole authority.

**Evidence (live readback):**
- `t_3e8b3ba4` (board `hermes-chatgpt-mcp`): status **done** (run `1210`, reviewer, completed `1787691831`). Literal verdict **ADOPT_BEADS_AS_WORK_GRAPH**, confidence 0.61 conditional / 0.38 unconditional, fallback HYBRID_SHADOW_ONLY, pilot-scoped. 7 active parent edges (`t_4c9f3cff`, `t_09bb14ec`, `t_e167129b`, `t_d1d914e5`, `t_25d0ee59`, `t_8c0d9b55`, `t_2234b281`) consumed.
- `t_b65aff04` (board `hermes-chatgpt-mcp`): status **archived** (run `1209`, reviewer, reclaimed `1787691822`, archived `1787691823`). No verdict was emitted — it was reclaimed BEFORE any verdict, per coordinator comment `1787691819`: *"fresh review t_3e8b3ba4 (G2) is the sole canonical Beads verdict authority ... This predecessor review is superseded for verdict purposes; preserve any output only as historical comparison."*
- Downstream decision-package `t_8fa8f4ff` (BEADS-SPIKE-5): edge **rebound** recorded `parent=t_b65aff04 → child=t_8fa8f4ff` with `edge_state=rebound`, `replaced_by_parent_id=t_3e8b3ba4`, `recovery_relation_id=beads-review-reconcile-20260825` (event `1787691950`). The new active edge is `parent=t_3e8b3ba4 → child=t_8fa8f4ff`.

**Fail-closed implication:** A non-atomic rewire window exists; the historical review must be treated as `rebound`/`archived` (zero gating power) and never re-promoted to a second canonical verdict. The G2 verdict artifact `BEADS-SPIKE-4-G2-FINAL-VERDICT.md` (sha256 `7e9c61e4f2515a07a61f5e55371ab0a2fc2d6b81e3f78eaa0f0bf3c4b37bc785`) is the only canonical verdict evidence.

---

## 2. Status-terminal dependency semantics treated manage review NEEDS_CHANGES as ready — bridge dependency-held and reparented to fresh review

**Finding:** `t_0b4f1e30` (BEADS-TRANSITION-BRIDGE) was originally parented to `t_3e8b3ba4` + `t_1b9f7a13` (manage review). Because `t_1b9f7a13` returned **NEEDS_CHANGES** (not a clean PASS), the bridge must not proceed on status-terminal semantics alone. It was dependency-held and reparented to the fresh re-review `t_5a28c3de`.

**Evidence (live readback):**
- `t_1b9f7a13` (board `hermes-chatgpt-mcp`): status **done**, verdict **NEEDS_CHANGES** (run `1206`, reviewer, completed `1787691113`). Blocking findings B1 (priority-only edit on claimed running task not in running-claim guard) and B2 (update_task returns requested fields not actual changed_fields, breaks idempotency).
- `t_0b4f1e30` (board `hermes-chatgpt-mcp`): run `1213` (kanban-coordinator) **blocked** `1787692228` — *"Wait for fresh Hermes manage remediation and independent re-review after t_1b9f7a13 NEEDS_CHANGES; Beads verdict alone does not authorize transition."* Two edge_retired events:
  - `parent=t_1b9f7a13 → child=t_0b4f1e30` with `edge_state=rebound`, `replaced_by_parent_id=t_5a28c3de`, `recovery_relation_id=manage-review-reconcile-20260825` (`1787692230`).
  - `parent=t_5a28c3de → child=t_0b4f1e30` with `edge_state=rebound`, `replaced_by_parent_id=t_6582d87c`, `recovery_relation_id=manage-review-route-guard-20260825` (`1787692723`).
- `t_5a28c3de` (board `hermes-chatgpt-mcp`): status **todo** (reviewer), parent `t_09dd433e` (fresh B1/B2 remediation). Its own edge to `t_0b4f1e30` is `rebound` pending the remediation chain.

**Fail-closed implication:** NEEDS_CHANGES ≠ PASS. A review returning NEEDS_CHANGES does not satisfy a "both parents terminal" gating rule. The bridge stays dependency-held until the fresh re-review (`t_5a28c3de`) reaches terminal PASS. Reparenting used the canonical soft-retire/replacement-provenance primitive — no hard delete.

---

## 3. Adding G2 parent caused t_8fa8f4ff to start before parent verdict was terminal — explicit dependency block

**Finding:** When `t_3e8b3ba4` (G2) was bound as a parent of `t_8fa8f4ff` (BEADS-SPIKE-5 decision package), the child began executing while G2 was still RUNNING and had not emitted a literal verdict. An explicit dependency block was applied until G2 reached terminal status with a read-back verdict.

**Evidence (live readback):**
- `t_8fa8f4ff` (board `hermes-chatgpt-mcp`): run `1211` (kanban-coordinator) **blocked** `1787691981` — *"Wait for sole canonical G2 verdict t_3e8b3ba4 before decision-package execution."* Coordinator comment `1787691981`: *"FAIL-CLOSED DEPENDENCY HOLD 2026-08-25: G2 t_3e8b3ba4 is still RUNNING and has not emitted a literal verdict."*
- After G2 completed (`1787691831`), `t_8fa8f4ff` run `1212` completed `1787693128` having consumed the literal verdict ADOPT_BEADS_AS_WORK_GRAPH (verified by sha256 `7e9c61e4f2515a07a61f5e55371ab0a2fc2d6b81e3f78eaa0f0bf3c4b37bc785`).

**Fail-closed implication:** A freshly linked parent edge must not be treated as satisfied until the parent is terminal AND its exact verdict/artifact has been read back. Dependency promotion must gate on terminal status + read-back, not on link existence.

---

## 4. Copied Gate-A hashes were not byte-exact — detected by live metadata readback, archived before execution, replaced with corrected t_c560b950

**Finding:** An earlier Gate-A surface-rectification preparation carried copied hash/identity fields that were not byte-exact against the verified live metadata readback. The discrepancy was caught by re-reading live identity (service PID, `/healthz`, build.json, installed server.py sha256, env `MCP_SURFACE`) before any execution, the defective preparation was archived, and a corrected Gate-A prep `t_c560b950` was produced from the exact `t_024deb64` preflight artifacts.

**Evidence (live readback):**
- `t_024deb64` (board `hermes-chatgpt-mcp`): status **done** (run `1202`, investigator, completed `1787690695`), READ-ONLY preflight. Exact readback: `from_commit=d7eba25ea8f692d2d0b65d7e5044df79e94c8a92`; `wheel_sha256=757b25ebe95429ccc16b10d9f922c71b3be9fbd3d23217d3ed50d447550c3432`; `server_py_sha256=14c737c3794f579bde0313fb2ca6874f67f3ee1c11ff1d3a96982318d938c043`; `gate_package_sha256=4f94c0957a81eb62b3a55d3addb50dd3f55085c889690d32730d031ee737da5d`; `report_sha256=941ed0cffb485e49b2a6b2d4afd3da54914cb812de05358cca12e551ccdcce0c`; `live_pid=580052`; `live_healthz_surface=stable`; `env_surface=beta`. S0 mismatch confirmed (healthz stable vs oauth manage-advertising).
- `t_c560b950` (board `hermes-chatgpt-mcp`): status **done** (run `1214`, operator, completed `1787695494`). Both attachments sha256-verified against the readback; field comparison shows MATCH on every field. Canonical package written to `/home/ubuntu/.hermes/kanban/human_gates/t_c560b950.gate-package.json`. `not_proven_emitted=false` — no field differed, so NOT_PROVEN was not triggered. ZERO mutations performed.
- Gate decision `t_d6f5db30` (board `hermes-chatgpt-mcp`): status **done** (run `1217`, operator, completed `1787695627`). Literal YES comment posted `2026-08-25T22:05Z` after fail-closed re-verification. **This card is a decision record only; it executes nothing.** The YES consumes the nonce for one bounded execution card (OP-A0..A3) to follow — no execution has occurred in this evidence window.

**Fail-closed implication:** Copied identities are never authoritative. Every hash/commit/PID/surface field must be re-read live and byte-compared against the verified preflight before a gate is materialized or a YES is honored. A single non-matching field ⇒ NOT_PROVEN ⇒ no authorization. The corrected card replaced the defective one via archiving (no hard delete), preserving the auditable history.

---

## 5. Surface healthz remains stable while env advertises beta and no Human Gate has executed

**Finding:** As of the latest live readback cited by the gate chain, the runtime surface attestation (`/healthz` `surface=stable`) disagrees with the deployed environment (`MCP_SURFACE=beta`, which advertises `hermes:manage` via BETA_AUTH_POLICY). The surface-rectification Human Gate (Gate-A) has had a literal YES recorded, **but no execution card has yet been spawned to perform OP-A0..A3** — i.e. no Human Gate *operation* has executed.

**Evidence (live readback, re-verified at gate-prep 2026-08-25T21:35Z and at YES 2026-08-25T22:05Z):**
- Service `hermes-chatgpt-mcp.service` active, PID `580052`.
- `/healthz`: `{build_commit d7eba25ea8f692d2d0b65d7e5044df79e94c8a92, surface stable, deployed_at 2026-08-25T14:57:57Z}`.
- `/var/lib/hermes-chatgpt-mcp/build.json`: d7eba25 stable, `deployed_at 2026-08-25T15:13:56Z`.
- `env MCP_SURFACE=beta` unchanged; oauth `scopes_supported` includes `hermes:manage`.
- S0 mismatch STILL LIVE; ALREADY_BETA not triggered.
- `t_d6f5db30` run summary: *"This card is a decision record only and executes nothing."* No OP-A0..A3 execution card appears in the evidence window.

**Fail-closed implication:** A recorded YES is a *decision record*, not an execution. Until an execution card bound to the verified package sha256 + nonce actually performs OP-A0..A3 and posts post-restart read-back (OP-A3), the live surface remains `stable`. No claim of surface beta, restart, or deploy is valid. GATE_B (`t_f03540c0`) remains unexecuted and must not be bundled with GATE_A.

---

## 6. V4 W2 blocked for truncated contract; accidental diff restored; spec recovery t_325d35d2 created

**Finding:** `t_d79a37bb` (V4-WAVE-2 · IMPLEMENT) was blocked because its recovered task body was truncated/incomplete and could not identify a verifiable functional change. A worker had restored an accidental 15-line diff to `server.py` during recovery. A spec-recovery generation `t_325d35d2` was created to reconstruct the canonical contract.

**Evidence (live readback, board `hermes-v4-planning`):**
- `t_d79a37bb`: status **blocked** (run `57`, coder, ended `1787688018`). Summary: *"El cuerpo del task recuperado está truncado/incompleto y no permite identificar con seguridad el cambio funcional requerido. Restauré la edición accidental de server.py; la sintaxis pasa, pero no debo inventar requisitos ni implementar sin una especificación verificable."* Escalation comment `1787688015` notes `git diff --stat` shows only `hermes_chatgpt_mcp/server.py | 15 deletions`; `py_compile` passes; single spurious `scripts/_wave2_probe.py` removed. Parent edge `t_081dcd0d → t_d79a37bb` is `retired` (`replaced_by=t_b8410d63`, `recovery=rewire-run-1`); active parent is `t_b8410d63`.
- `t_325d35d2` (V4-WAVE-2-SPEC-RECOVERY-G2): status **done** (run `61`, software-architect, `1787692237`→`1787692731`). Verdict **CONDITIONAL PASS** — produced durable 41 KB / 356-line spec pinned to baselines `d7eba25`/`885e9ef`/`ef22` and W0 candidate `b6ea...` (b6da006), with exact input shapes. Child edge `t_325d35d2 → t_050fc9b6` active.
- Fresh implementation `t_050fc9b6` (V4-WAVE-2-G2 · IMPLEMENT): status **done** (run `63`, coder, `1787692853`→`1787694422`), candidate commit `5e3d6fba3d07350b62668da4c2084fcd7cfd5c2e`, in fresh worktree off `d7eba25` merging `b6da006`. Downstream `t_86ca5d96` (TEST) and `t_1060ca75` (DOGFOOD) rebound active.
- Generation-rollover coordinator comment `1787692839`: *"Preserve this blocked predecessor/worktree as historical evidence; do not unblock or implement from its truncated body. Fresh implementation must use explicit worktree wt/t_d79a37bb-fresh ... consume the 356-line recovery spec."*

**Fail-closed implication:** A truncated/incomplete contract is a hard block, not a guess. The accidental diff was reverted to base; no functional change was invented. Recovery reproduces the contract from durable evidence rather than restarting from zero. Predecessor worktree/evidence preserved, never hard-deleted.

---

## 7. V4 W3 completed with pytest/compile/diff evidence; ruff unavailable — must remain NOT_EXECUTED

**Finding:** `t_6d8f0f8e` (V4-WAVE-3 · IMPLEMENT — Attachments/Remote Client) completed and `t_b230c1b6` (V4-WAVE-3 · TEST) completed and reported PASS on pytest/compile/diff evidence, but `ruff` was unavailable in the execution environment and its check must remain recorded as **NOT_EXECUTED**, not as a pass.

**Evidence (live readback, board `hermes-v4-planning`):**
- `t_6d8f0f8e`: status **done** (run `59`, coder, completed). Implemented Wave-3 remote attachment transport (content_base64, size-cap enforcement, filename/MIME/hash validation, provenance return without exposing server paths).
- `t_b230c1b6` (V4-WAVE-3 · TEST): status **done** (run `62`, coder, completed). Summary: *"Implemented and tested Wave-3 remote attachment transport ... All tests pass."* Conductor checkpoint (parent `t_f00c7f56` comment `1787692506`) records: *"t_6d8f0f8e W3 implementation DONE with 205 pytest passed, 3 attachment, 15 regression, compile/diff checks PASS and ruff NOT_EXECUTED."*

**Fail-closed implication:** Absent a tool (ruff) is **NOT** a pass. The lint gate is explicitly NOT_EXECUTED and must not be inferred as satisfied. Any downstream gate/release that requires ruff must treat it as an open gate, not closed. The pytest/compile/diff evidence stands; the ruff absence is a documented gap, not a silent win.

---

## 8. Cross-board recovery / rebound rules (recovered from the G2 conductor record)

1. **Never infer graph truth from a task body.** Edge state, verdicts, statuses, and rebind history live in the board DB (`task_links`, `task_events`, `task_runs`), not in prose. Re-read before acting.
2. **Soft-retire, never hard-delete.** Every generation rollover / review reconciliation used `edge_retired` with `replaced_by_parent_id` + `recovery_relation_id` provenance, or `link_tasks` for fresh edges. No raw SQL delete, no `DELETE` of edges or tasks.
3. **Preserve historical edges.** Reclaimed/archived cards (`t_b65aff04`) and blocked predecessors (`t_d79a37bb`) keep their rows; rebind is a state transition, not a removal.
4. **No-op retire is correct when no edge exists.** For `t_1060ca75` (DOGFOOD), the old `t_d79a37bb` parent edge never existed (it was created with parent `t_86ca5d96` only; `t_050fc9b6` was later *linked*, not retired-in). The attempted old-edge retire correctly produced no edge to retire — no error, no mutation. Record the exact error if one occurs; here the no-op is the expected, safe outcome.
5. **Fail-closed dependency promotion.** A child may promote only after the parent is terminal AND its exact verdict/artifact has been read back (§2, §3). NEEDS_CHANGES and RUNNING are not "ready".
6. **Byte-exact gate preparation.** Every Gate-A/B field must be re-read live and sha256-compared against the verified preflight; any mismatch ⇒ NOT_PROVEN ⇒ no gate. A YES is a decision record, not an execution (§4, §5).
7. **Truncated contract = hard block.** Do not invent requirements; recover the contract from durable evidence and implement only from the recovered spec (§6).
8. **Unavailable check ≠ pass.** ruff NOT_EXECUTED is an open gate, not a silent pass (§7).

---

*Reconciliation performed by github-steward under task `t_1da73350` (DOGFOOD-CHECKPOINT-20260825-G2). All task/run/edge assertions re-verified by direct SQLite read of the owning board (`hermes-chatgpt-mcp` or `hermes-v4-planning`) as of 2026-08-25 (UTC). This is a point-in-time truth-sync, not live state — re-derive from the board and live readback before any decision. No deploy/restart/OAuth/DCR/cutover/PASS is claimed beyond the exact evidence cited. SHAs are attributed to their owning repo; do not conflate `hermes-chatgpt-mcp` with `hermes-agent` or `hermes-v4-planning`.*
