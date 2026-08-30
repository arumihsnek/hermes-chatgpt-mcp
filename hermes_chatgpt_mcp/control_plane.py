# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92 (V4-BASELINE.md §1)
# Candidate: wt/t_78ac0513 — Wave-4 control-plane differential (portable, bounded, auditable).
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Literal

from .provenance import API_VERSION, bind_candidate_provenance_to_task, get_baseline, get_candidate_provenance
from .release import BuildMetadataError, canary_manifest

# ── Clean-architecture boundaries ──────────────────────────────────────────
# Domain policy (this module) owns the gate/canary/status shapes and rules.
# It does NOT import server.py, FastMCP, or any adapter implementation type
# beyond the duck-typed read/command ports described below.  Adapters
# (hermes_cli.kanban_db) live outside; this module maps to/from them.

DELIVERY_MODES: frozenset[str] = frozenset({"notify", "notify+wake", "wake"})
SUPPORTED_CONTROL_STATUS_ACTIONS: frozenset[str] = frozenset({"status", "snapshot"})
SUPPORTED_PAUSE_STATUS = frozenset({"active", "paused", "unknown"})

# Evidence budget so a gate payload can never page-large.
_MAX_EVIDENCE_CHARS = 8000
_MAX_RISK_ITEMS = 10
_MAX_ROLLBACK_CHARS = 2000


# ── Canonical records / identity ───────────────────────────────────────────

@dataclass(frozen=True)
class GateCandidateProvenance:
    candidate_sha: str | None
    candidate_branch: str | None
    baseline_branch: str
    baseline_mcp_sha: str
    baseline_hermes_sha: str
    baseline_phase_s_sha: str
    api_version: str
    surface: str
    provenance_header: str


@dataclass(frozen=True)
class GateEvidence:
    task_id: str
    task_title: str
    task_status: str
    latest_summary: str | None
    result_excerpt: str | None
    parent_ids: list[str]
    child_ids: list[str]
    dispatch_state: str
    dispatch_reasons: list[str]
    truncated: bool


@dataclass(frozen=True)
class HumanGateContext:
    """Bounded, point-in-time bundle the reviewer uses to decide YES/NO.

    No mutation is performed to build this context.  The human's decision
    is recorded separately (comment + explicit state transition) and is
    auditable via task_events.  Self-approval is rejected structurally:
    the actor recording a decision must differ from the actor that built the
    gate context when the gate was created by a worker (enforced by
    validate_gate_actor).
    """

    task_id: str
    board: str
    provenance: GateCandidateProvenance
    evidence: GateEvidence
    residual_risk: tuple[str, ...]
    rollback: str
    decision_options: tuple[str, str] = ("YES", "NO")
    generated_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["residual_risk"] = list(self.residual_risk)
        d["decision_options"] = list(self.decision_options)
        return d


@dataclass(frozen=True)
class CanaryBundle:
    manifest: dict[str, str]
    verified: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class BoundedStatusSnapshot:
    board: str
    generated_at: int
    daemon: dict[str, Any]
    stats: dict[str, Any]
    dispatch_dry_run: dict[str, Any] | None
    notify_count: int | None
    control_plane: dict[str, str]


# ── Pure helpers ───────────────────────────────────────────────────────────

def _clip(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    s = str(text)
    return s[:limit] if len(s) > limit else s


def provenance_bundle(surface: Literal["stable", "beta"] = "stable") -> GateCandidateProvenance:
    prov = get_candidate_provenance(surface=surface)
    base = get_baseline()
    return GateCandidateProvenance(
        candidate_sha=prov.candidate_sha,
        candidate_branch=prov.candidate_branch,
        baseline_branch=base.branch,
        baseline_mcp_sha=base.mcp_sha,
        baseline_hermes_sha=base.hermes_sha,
        baseline_phase_s_sha=base.phase_s_sha,
        api_version=base.api_version,
        surface=surface,
        provenance_header=prov.provenance_header(surface),
    )


def build_residual_risk(reasons: list[str], *, residual: list[str] | None = None) -> tuple[str, ...]:
    items = list(residual or [])
    # Surface dispatch blockers as risk so the human sees why the gate exists.
    for reason in reasons[:3]:
        if reason not in items:
            items.append(f"dispatch: {reason}")
    return tuple(items[:_MAX_RISK_ITEMS])


def build_rollback_text(board: str, task_id: str) -> str:
    # Rollback is deliberately one sentence + one command the operator can
    # copy.  No live promotion is ever implied here; canary remains detached.
    text = (
        f"Board {board} task {task_id}: no live promotion in Wave 4. "
        f"To roll back a canary, redeploy the prior build_commit via the "
        f"existing deploy pipeline; MCP state requires no migration. "
        f"Evidence: task_events + task_runs remain authoritative."
    )
    return _clip(text, _MAX_ROLLBACK_CHARS) or text


def validate_gate_actor(*, requester: str | None, actor: str | None) -> None:
    """Reject self-approval.

    A worker that created a gate context must not be the actor that records
    the YES.  When either side is unknown (e.g. offline harness), the check
    is skipped — the audit trail still distinguishes the two events.
    """
    if requester and actor and requester.strip() == actor.strip():
        raise ValueError("human gate self-approval is forbidden: decision actor must differ from requester")


# Requester identities reserved for workers whose candidate was superseded or
# retired; a YES recorded on their behalf would approve a stale candidate, so
# it fails closed instead of landing in the audit trail.
_STALE_REQUESTER_MARKERS = ("superseded", "retired", "stale", "archived")


def validate_gate_requester(requester: str | None) -> None:
    """Reject decisions bound to a stale/superseded candidate requester.

    A human-gate decision must be bound to the live candidate that produced
    the evidence bundle. When the named requester carries a supersession
    marker (e.g. a worker session replaced by a rebind), the candidate is
    no longer the one under review, so recording a decision for it would
    launder approval through a dead provenance chain — fail closed instead.
    """
    if not requester:
        return
    normalized = requester.strip().lower()
    if any(marker in normalized for marker in _STALE_REQUESTER_MARKERS):
        raise ValueError("human gate decision rejected: requester belongs to a stale or superseded candidate")


def validate_delivery_mode(mode: str | None) -> str | None:
    if mode is None:
        return None
    if mode not in DELIVERY_MODES:
        raise ValueError(f"unsupported delivery mode: {mode!r} (expected one of {sorted(DELIVERY_MODES)})")
    return mode


# ── Adapter-facing use cases (duck-typed ports) ────────────────────────────
#
# Ports:
#   ReadPort  — get_task(task_id) -> TaskDetail, get_activity(task_id) -> ActivityView,
#               get_dispatch(task_id) -> DispatchView, stats() -> dict
#   ManagePort— daemon(action) -> DaemonResult, dispatch(dry_run=True) -> dict
#
# The concrete port objects are HermesReadOnlyAdapter / HermesCardManagementAdapter
# but this module never imports them directly — it accepts any object exposing
# the named methods (structural typing).

def build_gate_context(
    *,
    read_adapter: Any,
    board: str,
    task_id: str,
    surface: Literal["stable", "beta"] = "stable",
    residual_risk: list[str] | None = None,
) -> HumanGateContext:
    task = read_adapter.get_task(task_id)
    task_bound = bind_candidate_provenance_to_task(getattr(task, "body", "") or "")
    if task_bound is None:
        prov = provenance_bundle(surface)
    else:
        base = task_bound.baseline
        prov = GateCandidateProvenance(
            candidate_sha=task_bound.candidate_sha,
            candidate_branch=task_bound.candidate_branch,
            baseline_branch=base.branch,
            baseline_mcp_sha=base.mcp_sha,
            baseline_hermes_sha=base.hermes_sha,
            baseline_phase_s_sha=base.phase_s_sha,
            api_version=base.api_version,
            surface=surface,
            provenance_header=task_bound.provenance_header(surface),
        )
    activity = read_adapter.get_activity(task_id, max_items=20, log_bytes=0)
    dispatch = read_adapter.get_dispatch(task_id)

    # Keep evidence bounded.  TaskDetail exposes result (not result_excerpt);
    # the summary field on TaskSummary/TaskDetail is named latest_summary.
    latest_summary = _clip(getattr(task, "latest_summary", None), 1200)
    result_excerpt = _clip(getattr(task, "result", None), 1200)

    evidence = GateEvidence(
        task_id=str(task.id),
        task_title=str(task.title)[:300],
        task_status=str(task.status),
        latest_summary=latest_summary,
        result_excerpt=result_excerpt,
        parent_ids=list(getattr(task, "parent_ids", []) or [])[:16],
        child_ids=list(getattr(task, "child_ids", []) or [])[:16],
        dispatch_state=str(getattr(dispatch, "state", "UNKNOWN")),
        dispatch_reasons=list(getattr(dispatch, "reasons", []) or [])[:10],
        truncated=bool(getattr(activity, "truncated", False)),
    )

    risks = build_residual_risk(evidence.dispatch_reasons, residual=residual_risk)
    rollback = build_rollback_text(board, task_id)

    return HumanGateContext(
        task_id=str(task.id),
        board=board,
        provenance=GateCandidateProvenance(
            candidate_sha=prov.candidate_sha,
            candidate_branch=prov.candidate_branch,
            baseline_branch=prov.baseline_branch,
            baseline_mcp_sha=prov.baseline_mcp_sha,
            baseline_hermes_sha=prov.baseline_hermes_sha,
            baseline_phase_s_sha=prov.baseline_phase_s_sha,
            api_version=prov.api_version,
            surface=prov.surface,
            provenance_header=prov.provenance_header,
        ),
        evidence=evidence,
        residual_risk=risks,
        rollback=rollback,
        generated_at=int(time.time()),
    )


def format_gate_markdown(ctx: HumanGateContext) -> str:
    p = ctx.provenance
    e = ctx.evidence
    risks = "\n".join(f"- {r}" for r in ctx.residual_risk) or "- (none declared)"
    return (
        f"# Human Gate — {ctx.task_id} on {ctx.board}\n\n"
        f"**Provenance** `{p.provenance_header}` · API `{p.api_version}` · "
        f"baseline `{p.baseline_branch}@{p.baseline_mcp_sha[:7]}` · surface `{p.surface}`\n\n"
        f"**Task** `{e.task_title}` — status `{e.task_status}` · dispatch `{e.dispatch_state}`\n"
        f"Reasons: {', '.join(e.dispatch_reasons) or '(none)'}\n\n"
        f"**Latest summary**\n{(e.latest_summary or '(none)')[:800]}\n\n"
        f"**Residual risk**\n{risks}\n\n"
        f"**Rollback**\n{ctx.rollback}\n\n"
        f"**Decision** — reply with exactly one of: `YES` (proceed) or `NO` (block and state reason). "
        f"Self-approval is rejected; the deciding actor must differ from the requester.\n"
    )


def build_canary_bundle(*, build_commit: str, surface: str, deployed_at: str) -> CanaryBundle:
    try:
        manifest = canary_manifest(build_commit=build_commit, surface=surface, deployed_at=deployed_at)
        # Round-trip through JSON to ensure it is serializable and frozen.
        text = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        parsed = json.loads(text)
        assert isinstance(parsed, dict)
        return CanaryBundle(manifest=manifest, verified=True, errors=())
    except (ValueError, BuildMetadataError) as exc:
        return CanaryBundle(manifest={}, verified=False, errors=(str(exc),))


def verify_canary_manifest(payload: dict[str, Any]) -> CanaryBundle:
    """Fail-closed verifier for a canary manifest dict (no file I/O).

    Baseline-contract fields are pinned to the frozen v4 baseline: a manifest
    that names any other branch/sha/api_version is rejected, so a canary can
    never borrow provenance it was not built against.
    """
    try:
        build_commit = payload.get("build_commit")
        surface = payload.get("surface")
        deployed_at = payload.get("deployed_at")
        if not isinstance(build_commit, str) or not isinstance(surface, str) or not isinstance(deployed_at, str):
            raise BuildMetadataError("invalid release metadata")
        base = get_baseline()
        for field, expected in (
            ("api_version", base.api_version),
            ("baseline_branch", base.branch),
            ("baseline_mcp_sha", base.mcp_sha),
        ):
            value = payload.get(field)
            if value is not None and value != expected:
                raise BuildMetadataError(f"invalid release metadata field: {field}")
        manifest = canary_manifest(build_commit=build_commit, surface=surface, deployed_at=deployed_at)
        return CanaryBundle(manifest=manifest, verified=True)
    except (ValueError, BuildMetadataError) as exc:
        return CanaryBundle(manifest={}, verified=False, errors=(str(exc),))


def bounded_notify_subscribe(
    *,
    manage_adapter: Any,
    task_id: str,
    platform: str,
    chat_id: str,
    thread_id: str | None = None,
    delivery: str | None = None,
) -> dict[str, Any]:
    """Single-shot, bounded subscribe — no loop, durable row, idempotent.

    The returned dict mirrors HermesCardManagementAdapter.notify_subscribe but
    validates the delivery mode before touching the DB.
    """
    validate_delivery_mode(delivery)
    return manage_adapter.notify_subscribe(task_id, "", platform=platform, chat_id=chat_id, thread_id=thread_id, delivery=delivery)


def bounded_notify_list(*, manage_adapter: Any, task_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    # Enforce the same 1..1000 bound as the schema so a caller cannot page
    # without limit and turn list into an open scan.
    if not 1 <= limit <= 1000:
        raise ValueError("notify list limit must be between 1 and 1000")
    return manage_adapter.notify_list(limit=limit, task_id=task_id)


def pause_status() -> dict[str, Any]:
    """Read-only pause signal.

    Hermes supports a global ESTOP sentinel at $HERMES_HOME/ESTOP; this
    probe is read-only, never mutates it, and reports unknown when the
    sentinel location is indeterminate.  There is no MCP mutation for
    pause/resume in Wave 4 — the human uses the gateway/host tooling.
    """
    home_raw = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
    sentinel = Path(home_raw).expanduser() / "ESTOP"
    try:
        if sentinel.is_file():
            text = sentinel.read_text(encoding="utf-8", errors="ignore")[:500]
            return {"paused": True, "sentinel": str(sentinel), "detail": _clip(text, 500)}
        return {"paused": False, "sentinel": str(sentinel)}
    except Exception as exc:  # pragma: no cover - filesystem race
        return {"paused": False, "sentinel": str(sentinel), "error": str(exc)[:300], "status": "unknown"}


def drain_preview(*, manage_adapter: Any) -> dict[str, Any]:
    """Bounded drain preview: gc dry_run only, never a live drain.

    A real drain is dispatch + worker lifecycle; this preview surfaces the
    counts that would be cleaned without deleting anything.
    """
    return manage_adapter.gc(dry_run=True)


def status_snapshot(
    *,
    read_adapter: Any,
    manage_adapter: Any,
    board: str,
    include_dispatch_dry_run: bool = True,
) -> BoundedStatusSnapshot:
    now = int(time.time())
    daemon = manage_adapter.daemon(action="status")
    stats = manage_adapter.stats()
    notify_count: int | None = None
    try:
        notify_count = len(manage_adapter.notify_list(limit=100, task_id=None))
    except Exception:
        notify_count = None

    dispatch_dry = None
    if include_dispatch_dry_run:
        try:
            dispatch_dry = manage_adapter.dispatch(dry_run=True)
        except Exception as exc:  # pragma: no cover
            dispatch_dry = {"error": str(exc)[:500]}

    return BoundedStatusSnapshot(
        board=board,
        generated_at=now,
        daemon=daemon if isinstance(daemon, dict) else dict(daemon),
        stats=stats if isinstance(stats, dict) else dict(stats),
        dispatch_dry_run=dispatch_dry,
        notify_count=notify_count,
        control_plane={
            "api_version": API_VERSION,
            "baseline_branch": get_baseline().branch,
            "mode": "bounded-snapshot",
        },
    )
