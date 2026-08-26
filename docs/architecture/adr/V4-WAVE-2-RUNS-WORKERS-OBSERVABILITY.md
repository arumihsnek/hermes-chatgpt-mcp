# ADR-002 · V4 Wave 2 Runs / Workers / Observability

Status: ACCEPTED · 2026-08-25
Baseline: MCP d7eba25 + verified Wave-0 candidate b6da006
Candidate worktree: wt/t_d79a37bb-fresh

## Context
Wave 2 adds bounded operational readback to the beta MCP surface. The canonical Hermes source is SQLite through `ReadOnlyHermesStore` (`mode=ro`, `PRAGMA query_only=ON`) and the Hermes `kanban_db` APIs. The required provenance chain is board task → active-edge dispatch projection → task run → worker/session fields → terminal outcome. Stable remains the existing eight-tool contract.

## Decision
Add beta-only read tools with strict `extra=forbid` envelopes:

- `get_run({board?, run_id: int >= 1})` uses canonical `Run.id`, not `TaskInput.task_id`; a missing row returns `RUN_NOT_FOUND`.
- `list_runs({board?, task_id, limit 1..200, include_active=true})` returns canonical chronological history and a truthful truncation bit.
- `active_workers({board?, limit 1..100})` projects running tasks joined to `current_run_id`, includes worker PID, claim/heartbeat, profile and session linkage, and host-scoped other-board counts.
- `bounded_log({board?, task_id, tail_bytes 0..32000, cursor?})` reads an exact byte tail and returns truncation/next-cursor metadata. The 32,000-byte ceiling is retained from the existing adapter contract (Q-1 resolved).
- `runtime_status({board?})` returns board stats, this-board running count, host-scoped other-board count, total, and a bounded daemon availability snapshot.

Configuration/build provenance remains the existing `/healthz` body and Wave-0 response headers; no second MCP provenance source is introduced (Q-2 resolved). Runtime status means Hermes host/runtime, not OpenResty process control (A-4/Q-2). There is no daemon start/stop, watch stream, signal function, or unbounded tail.

The existing `reclaim_task` command remains the guarded terminate/reclaim operation. It is canonical, board-pinned, scope-gated, row-count guarded, and idempotent only for the successful first transition. Dispatch remains admin-gated; its canonical `dispatch_once` lock reports `skipped_locked` on contention and dry-run performs no writes. Active-edge-only dispatch fallback remains unchanged.

## Security and boundedness
All new reads use the resolved explicit board and read-only adapter. Authorization is checked before adapter construction. Cross-board write grants remain fail-closed. New schemas enforce numeric ceilings, and `_safe_data`/`_clip` protect metadata, summaries and errors. Physical paths, environment values and credentials are not projected.

## Consequences and verification
Wave-2 readback is additive and beta-only. Stable and ChatGPT compatibility surfaces retain their frozen tool allowlists. A-2 is resolved to `Run.id`; Q-1 is resolved to `tail_bytes <= 32000`; Q-2 is resolved in favor of `/healthz` plus headers; Q-3 is resolved by retaining reclaim as the only MCP terminate path; Q-4 is resolved by board-aware `ReadOnlyHermesStore.log_path` first, with canonical Hermes log fallback.

Rollback is a local Git revert of the Wave-2 candidate commits; no database migration, deploy, restart, OAuth mutation, traffic switch or history rewrite is needed. Verification includes adapter run/log/runtime projections, running-worker join tests, strict schema bounds, stable-surface parity, beta tool registration, and `RUN_NOT_FOUND` mapping.
