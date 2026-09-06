# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92 (V4-BASELINE.md §1)
# Candidate: wt/t_78ac0513 — Wave-4 control-plane differential (portable, bounded, auditable).
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Literal

from .provenance import (
    API_VERSION,
    ArtifactCandidateBinding,
    CandidateBinding,
    GitCandidateBinding,
    bind_candidate_provenance_to_task,
    get_baseline,
    get_candidate_provenance,
)
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
    binding: CandidateBinding | None = None

    @property
    def binding_fingerprint(self) -> str | None:
        if self.binding is None:
            return None
        from .provenance import candidate_binding_fingerprint

        return candidate_binding_fingerprint(self.binding)


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
        d["provenance"]["binding_fingerprint"] = self.provenance.binding_fingerprint
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
        binding=prov.binding,
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


class HumanGateDagViolation(ValueError):
    """Raised when a link/decompose would reverse Human-Gate authority direction.

    Canonical ordering is PRE-GATE evidence -> GATE -> POST-GATE mutation/review.
    A post-gate task (a descendant of its authorizing gate) must never become an
    ancestor/parent of that gate, nor of any ancestor gate, otherwise the gate's
    authority is bypassed and the human decision loses provenance.
    """


class HumanGateAuthorityDrift(ValueError):
    """Raised when a retained local verifier disagrees with canonical state.

    Canonical Human Gate/binding readback is authoritative. A locally retained
    fingerprint that does not match the canonical binding fingerprint is an
    incident — it fails closed here and must never silently override canonical
    state or authorize against it.
    """


@dataclass(frozen=True)
class GateDecisionRecord:
    """One parsed HUMAN_GATE comment: the exact decision plus the binding it authorized.

    ``binding_fingerprint`` is None for legacy comments recorded without a
    binding line. Legacy records can never authorize an exact canonical
    binding; only an exact fingerprint match preserves a decision.
    """

    decision: Literal["YES", "NO"]
    binding_fingerprint: str | None


def binding_fingerprint(
    *,
    candidate_sha: str | None,
    candidate_branch: str | None,
    baseline_mcp_sha: str,
    baseline_hermes_sha: str,
    baseline_phase_s_sha: str,
    api_version: str,
) -> str | None:
    """Return the canonical 8-hex binding fingerprint, or None for legacy provenance.

    Only an exact candidate binding (full SHA + explicit branch, as verified by
    ``bind_candidate_provenance_to_task``) yields a fingerprint. Running-build
    fallback provenance has no stable identity to authorize against, so it
    yields None and can never match a recorded YES. The 8-hex shape matches the
    ``binding_fingerprint`` slot rendered by the readback surface.
    """
    if not candidate_sha or not candidate_branch:
        return None
    material = "|".join(
        (
            candidate_sha.strip().lower(),
            candidate_branch.strip(),
            baseline_mcp_sha,
            baseline_hermes_sha,
            baseline_phase_s_sha,
            api_version,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]


_DECISION_HEAD_RE = re.compile(r"^HUMAN_GATE\s+(YES|NO)\b")
_BINDING_LINE_RE = re.compile(r"^Binding:\s*([0-9a-f]{8}|legacy)\s*$", re.IGNORECASE | re.MULTILINE)


def format_gate_decision_body(
    *,
    decision: Literal["YES", "NO"],
    task_id: str,
    board: str,
    reason: str | None = None,
    requester: str | None = None,
    binding_fingerprint: str | None = None,
) -> str:
    """Format the append-only HUMAN_GATE comment, binding the decision to a fingerprint.

    The trailing ``Binding:`` line is what lets a later reprepare/readback prove
    the recorded YES authorized *this* exact binding. ``None`` records
    ``Binding: legacy`` for decisions taken against running-build provenance.
    """
    body = f"HUMAN_GATE {decision}: {task_id} on {board}"
    if reason:
        body += f"\nReason: {reason[:2000]}"
    if requester:
        body += f"\nRequester: {requester[:200]}"
    body += f"\nBinding: {binding_fingerprint if binding_fingerprint else 'legacy'}"
    return body


def parse_recorded_gate_decisions(comments: Iterable[Any]) -> list[GateDecisionRecord]:
    """Parse HUMAN_GATE comments (records or dicts) into decision records.

    Non-gate comments are ignored. A gate comment without a parseable binding
    line is treated as legacy (``binding_fingerprint=None``) and can therefore
    never authorize an exact canonical binding.
    """
    records: list[GateDecisionRecord] = []
    for comment in comments:
        body = comment.get("body") if isinstance(comment, dict) else getattr(comment, "body", None)
        if not isinstance(body, str):
            continue
        head = _DECISION_HEAD_RE.search(body.strip())
        if head is None:
            continue
        match = _BINDING_LINE_RE.search(body)
        fingerprint: str | None = None
        if match is not None and match.group(1).lower() != "legacy":
            fingerprint = match.group(1).lower()
        records.append(
            GateDecisionRecord(
                decision="YES" if head.group(1) == "YES" else "NO",
                binding_fingerprint=fingerprint,
            )
        )
    return records


def resolve_gate_authority(
    *,
    canonical_fingerprint: str | None,
    decisions: Iterable[GateDecisionRecord],
) -> Literal["authorized", "denied", "needs_input"]:
    """Deterministically reprepare/read back the recorded human decision.

    A same unchanged ``binding_fingerprint`` preserves the already-recorded
    exact decision (YES -> authorized, NO -> denied; latest match wins). A
    changed fingerprint — or legacy provenance with no stable identity — always
    yields ``needs_input``: fresh human authority is required and approval is
    never automatic.
    """
    if canonical_fingerprint is None:
        return "needs_input"
    outcome: Literal["authorized", "denied", "needs_input"] = "needs_input"
    for record in decisions:
        if record.binding_fingerprint != canonical_fingerprint:
            continue
        outcome = "authorized" if record.decision == "YES" else "denied"
    return outcome


def assert_binding_parity(
    local_fingerprint: str | None,
    canonical_fingerprint: str | None,
) -> None:
    """Fail closed when a retained local verifier disagrees with canonical readback.

    Any disagreement — including a locally claimed exact fingerprint against
    legacy canonical provenance — raises :class:`HumanGateAuthorityDrift`
    instead of silently overriding canonical state.
    """
    if local_fingerprint != canonical_fingerprint:
        raise HumanGateAuthorityDrift(
            "human-gate binding parity failure: local verifier "
            f"({local_fingerprint or 'legacy'}) disagrees with canonical "
            f"readback ({canonical_fingerprint or 'legacy'})"
        )


def _task_body_text(task: Any) -> str:
    body = getattr(task, "body", None) or ""
    return str(body)


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
    task_bound = bind_candidate_provenance_to_task(
        getattr(task, "body", "") or "",
        task_reader=read_adapter.get_task,
        attachment_reader=getattr(read_adapter, "read_attachment_bytes", None),
    )
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
            binding=task_bound.binding,
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
            binding=prov.binding,
        ),
        evidence=evidence,
        residual_risk=risks,
        rollback=rollback,
        generated_at=int(time.time()),
    )


def revalidate_gate_context(
    *,
    read_adapter: Any,
    board: str,
    task_id: str,
    surface: Literal["stable", "beta"] = "stable",
    expected_binding_fingerprint: str | None,
) -> HumanGateContext:
    """Rebuild a gate and reject any candidate/review drift before a decision."""
    ctx = build_gate_context(
        read_adapter=read_adapter,
        board=board,
        task_id=task_id,
        surface=surface,
    )
    if ctx.provenance.binding_fingerprint != expected_binding_fingerprint:
        raise ValueError("human gate binding fingerprint is stale or missing")
    return ctx


def _binding_markdown(provenance: GateCandidateProvenance) -> str:
    binding = provenance.binding
    if isinstance(binding, ArtifactCandidateBinding):
        candidate = (
            f"kind `artifact` · task `{binding.candidate_task_id}` · "
            f"attachment `{binding.candidate_attachment_id}`"
            f" · SHA-256 `{binding.candidate_digest}` · source `{binding.source_ref}`"
        )
        review = (
            f"review task `{binding.review.task_id}` · attachment `{binding.review.attachment_id}` · "
            f"SHA-256 `{binding.review.digest}` · reviewed candidate "
            f"`{binding.review.reviewed_candidate_task_id}/{binding.review.reviewed_candidate_attachment_id}`"
        )
        return f"**Candidate binding** {candidate}\n**Review binding** {review}"
    if isinstance(binding, GitCandidateBinding):
        return (
            f"**Candidate binding** kind `git` · SHA `{binding.candidate_sha}` · "
            f"branch `{binding.branch}` · source `{binding.source_ref}`"
        )
    return "**Candidate binding** legacy running-build provenance"


def detect_human_gate_tasks(read_adapter: Any, candidate_task_ids: Iterable[str]) -> list[str]:
    """Return the subset of ``candidate_task_ids`` that are authorizing Human Gates.

    A task is treated as an authorizing gate when its body declares an exact
    candidate provenance (``bind_candidate_provenance_to_task`` succeeds with a
    full SHA), which is the canonical gate binding.  This is the same primitive
    ``build_gate_context`` relies on, so gate identity cannot drift between
    readback surfaces (item 2: canonical readback is authoritative).

    Only task bodies are inspected; no summary text, comment prose, or external
    provenance marker is trusted as a gate signal, so a crafted body cannot make
    an arbitrary task signable.
    """
    from .provenance import bind_candidate_provenance_to_task as _bind

    gates: list[str] = []
    for task_id in candidate_task_ids:
        try:
            body = getattr(read_adapter.get_task(task_id), "body", "") or ""
        except (LookupError, ValueError, RuntimeError):
            continue
        try:
            bound = _bind(body)
        except ValueError:
            # A body that declares an incomplete/invalid candidate is not an
            # authorizing gate; build_gate_context enforces strictness for the
            # gate context itself. Treating a non-binding body as non-gate keeps
            # the DAG direction guard read-only and fail-open at the identity
            # surface (authority is never granted by a failed declaration).
            bound = None
        if bound is not None:
            gates.append(str(task_id))
    return gates


def _descendants_of(conn: Any, hermes: Any, task_id: str, *, limit: int = 1024) -> set[str]:
    """Walk all descendants of ``task_id`` via the canonical ``child_ids`` port."""
    seen: set[str] = set()
    stack = [task_id]
    while stack:
        node = stack.pop()
        for child in hermes.child_ids(conn, node):
            if child in seen:
                continue
            seen.add(child)
            stack.append(child)
            if len(seen) >= limit:  # bounded safety valve
                return seen
    return seen


def assert_human_gate_dag_direction(
    *,
    read_adapter: Any,
    parent_id: str,
    child_id: str,
) -> None:
    """Fail-closed guard against reversing Human-Gate authority direction.

    Enforces PRE-GATE evidence -> GATE -> POST-GATE mutation/review. Linking
    ``parent_id -> child_id`` makes the parent an ancestor of the child and of
    everything below the child. That inverts gate authority exactly when some
    gate ``G`` at-or-below the child (``G`` is the child itself or one of its
    descendants) has the parent as its post-gate descendant: the post-gate task
    would become an ancestor of the authority that approved it — an authority
    cycle and a bypass of the recorded human decision.

    The legitimate direction is unaffected: linking a gate to its post-gate
    task, or pre-gate evidence to a gate, never matches the rule above and is
    allowed. A parent that is already downstream of the child is a plain
    authority cycle and is rejected as well; generic non-gate cycles remain the
    canonical layer's job.

    The check is structural and read-only: it inspects only the existing
    parent/child graph and gate identity. It raises
    :class:`HumanGateDagViolation` on any edge that would invert gate
    authority.
    """
    if parent_id == child_id:
        raise HumanGateDagViolation("a task cannot depend on itself")
    store = getattr(read_adapter, "store", None)
    hermes = getattr(read_adapter, "hermes", None)
    if store is None or hermes is None:
        # Without a read surface we cannot evaluate direction; fail closed.
        raise HumanGateDagViolation("human-gate DAG direction cannot be verified without a read adapter")
    with store.connect() as connection:
        descendants_of_child = _descendants_of(connection, hermes, child_id)
        gates = set(detect_human_gate_tasks(read_adapter, [child_id, *descendants_of_child]))
        for gate_id in gates:
            if parent_id in _descendants_of(connection, hermes, gate_id):
                raise HumanGateDagViolation(
                    f"linking parent {parent_id} -> child {child_id} reverses Human-Gate "
                    f"DAG direction: {parent_id} is post-gate of authorizing gate {gate_id} "
                    f"at-or-below {child_id} (post-gate task cannot become an ancestor of "
                    f"its authorizing gate)"
                )
        if parent_id in descendants_of_child:
            raise HumanGateDagViolation(
                f"linking parent {parent_id} -> child {child_id} creates an authority cycle: "
                f"{parent_id} is already downstream of {child_id}"
            )


def _all_ancestors(conn: Any, hermes: Any, task_id: str) -> list[str]:
    parents: list[str] = []
    frontier = [task_id]
    seen: set[str] = set()
    while frontier:
        next_frontier: list[str] = []
        for node in frontier:
            node_parents = list(hermes.parent_ids(conn, node))
            for parent in node_parents:
                if parent in seen:
                    continue
                seen.add(parent)
                parents.append(parent)
                next_frontier.append(parent)
        frontier = next_frontier
    return parents


def format_gate_markdown(ctx: HumanGateContext) -> str:
    p = ctx.provenance
    e = ctx.evidence
    risks = "\n".join(f"- {r}" for r in ctx.residual_risk) or "- (none declared)"
    return (
        f"# Human Gate — {ctx.task_id} on {ctx.board}\n\n"
        f"**Provenance** `{p.provenance_header}` · API `{p.api_version}` · "
        f"baseline `{p.baseline_branch}@{p.baseline_mcp_sha[:7]}` · surface `{p.surface}`\n\n"
        f"{_binding_markdown(p)}\n"
        f"**Binding fingerprint** `{p.binding_fingerprint or '(legacy)'}`\n\n"
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
