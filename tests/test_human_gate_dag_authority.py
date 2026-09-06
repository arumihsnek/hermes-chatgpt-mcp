"""Targeted regression fixtures for KANBAN-HG-DECOMPOSE-STARVATION-R1.

Historical shape: a gate task carrying an exact candidate binding, a recorded
human YES, a same-fingerprint reprepare/readback, and an attempted inverted
post-gate edge. Demonstrates correct edge direction (PRE-GATE -> GATE ->
POST-GATE) and decision persistence without touching live state.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from hermes_chatgpt_mcp import provenance
from hermes_chatgpt_mcp.control_plane import (
    HumanGateAuthorityDrift,
    HumanGateDagViolation,
    assert_binding_parity,
    assert_human_gate_dag_direction,
    binding_fingerprint,
    format_gate_decision_body,
    parse_recorded_gate_decisions,
    resolve_gate_authority,
)
from hermes_chatgpt_mcp.provenance import (
    BASELINE_HERMES_SHA,
    BASELINE_MCP_SHA,
    BASELINE_PHASE_S_SHA,
    API_VERSION,
)

CANDIDATE_SHA = "db9bebaee149b07e707fef66c33b8c05ced48766"
CANDIDATE_BRANCH = "mcp-ui-interactive-r1"
OTHER_SHA = "ff15b65fcd5ef6eb9a5dafeecd3c3b1d646607b8"

GATE_BODY = f"Activate exact candidate {CANDIDATE_SHA} on branch {CANDIDATE_BRANCH}."
PLAIN_BODY = "Plain task body with no exact candidate declaration."


def _canonical_fp(sha: str = CANDIDATE_SHA, branch: str = CANDIDATE_BRANCH) -> str:
    fp = binding_fingerprint(
        candidate_sha=sha,
        candidate_branch=branch,
        baseline_mcp_sha=BASELINE_MCP_SHA,
        baseline_hermes_sha=BASELINE_HERMES_SHA,
        baseline_phase_s_sha=BASELINE_PHASE_S_SHA,
        api_version=API_VERSION,
    )
    assert fp is not None and len(fp) == 8
    return fp


# ── Fake graph harness for the DAG guard ─────────────────────────────────────


class _FakeHermes:
    """Canonical parent_ids/child_ids port over an explicit child->parents map."""

    def __init__(self, parents: dict[str, list[str]]) -> None:
        self._parents = {k: list(v) for k, v in parents.items()}

    def parent_ids(self, conn: object, task_id: str) -> list[str]:
        return list(self._parents.get(task_id, []))

    def child_ids(self, conn: object, task_id: str) -> list[str]:
        return [child for child, ps in self._parents.items() if task_id in ps]


class _FakeStore:
    def __init__(self, hermes: _FakeHermes) -> None:
        self._hermes = hermes

    @contextmanager
    def connect(self):  # noqa: ANN204 — duck-typed store port
        yield object()


class _FakeRead:
    """Duck-typed read adapter: get_task bodies + store/hermes ports."""

    def __init__(self, bodies: dict[str, str], parents: dict[str, list[str]]) -> None:
        self._bodies = bodies
        self.hermes = _FakeHermes(parents)
        self.store = _FakeStore(self.hermes)

    def get_task(self, task_id: str) -> SimpleNamespace:
        if task_id not in self._bodies:
            raise LookupError(f"unknown task {task_id}")
        return SimpleNamespace(id=task_id, body=self._bodies[task_id])


@pytest.fixture()
def remote_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        provenance, "_verify_remote_candidate", lambda sha, branch, remote_name="origin": True
    )


@pytest.fixture()
def historical_shape(remote_ok: None) -> _FakeRead:
    """PRE-GATE t_evidence -> GATE t_gate -> POST-GATE t_post -> t_review."""
    return _FakeRead(
        bodies={
            "t_evidence": PLAIN_BODY,
            "t_gate": GATE_BODY,
            "t_post": PLAIN_BODY,
            "t_review": PLAIN_BODY,
            "t_other": PLAIN_BODY,
            "t_new": PLAIN_BODY,
        },
        parents={
            "t_gate": ["t_evidence"],
            "t_post": ["t_gate"],
            "t_review": ["t_post"],
        },
    )


# ── Item 1: DAG direction ────────────────────────────────────────────────────


def test_inverted_post_gate_edge_is_rejected(historical_shape: _FakeRead) -> None:
    with pytest.raises(HumanGateDagViolation, match="reverses Human-Gate"):
        assert_human_gate_dag_direction(
            read_adapter=historical_shape, parent_id="t_post", child_id="t_gate"
        )


def test_transitive_post_gate_edge_is_rejected(historical_shape: _FakeRead) -> None:
    with pytest.raises(HumanGateDagViolation, match="reverses Human-Gate"):
        assert_human_gate_dag_direction(
            read_adapter=historical_shape, parent_id="t_review", child_id="t_gate"
        )


def test_post_gate_to_ancestor_of_gate_is_rejected(historical_shape: _FakeRead) -> None:
    # t_evidence is above the gate; making post-gate t_post its parent would
    # route post-gate mutation above the authorizing gate.
    with pytest.raises(HumanGateDagViolation, match="reverses Human-Gate"):
        assert_human_gate_dag_direction(
            read_adapter=historical_shape, parent_id="t_post", child_id="t_evidence"
        )


def test_canonical_gate_to_post_gate_edge_is_allowed(historical_shape: _FakeRead) -> None:
    assert_human_gate_dag_direction(
        read_adapter=historical_shape, parent_id="t_gate", child_id="t_new"
    )
    assert_human_gate_dag_direction(
        read_adapter=historical_shape, parent_id="t_gate", child_id="t_post"
    )


def test_pre_gate_evidence_to_gate_is_allowed(historical_shape: _FakeRead) -> None:
    assert_human_gate_dag_direction(
        read_adapter=historical_shape, parent_id="t_other", child_id="t_gate"
    )


def test_self_link_and_plain_cycle_are_rejected(historical_shape: _FakeRead) -> None:
    with pytest.raises(HumanGateDagViolation, match="itself"):
        assert_human_gate_dag_direction(
            read_adapter=historical_shape, parent_id="t_gate", child_id="t_gate"
        )
    # t_gate -> t_post exists; linking t_post -> t_gate is the inverted shape,
    # while a non-gate cycle (t_review -> t_evidence path inverted) is caught
    # by the authority-cycle branch: t_evidence is downstream of nothing, but
    # t_post IS downstream of t_evidence, so t_post -> t_evidence is inversion
    # (covered above); a pure cycle with no gate:
    plain = _FakeRead(bodies={"a": PLAIN_BODY, "b": PLAIN_BODY}, parents={"b": ["a"]})
    with pytest.raises(HumanGateDagViolation, match="authority cycle"):
        assert_human_gate_dag_direction(read_adapter=plain, parent_id="b", child_id="a")


def test_guard_without_read_surface_fails_closed() -> None:
    with pytest.raises(HumanGateDagViolation, match="without a read adapter"):
        assert_human_gate_dag_direction(read_adapter=object(), parent_id="a", child_id="b")


# ── Item 2: canonical parity ─────────────────────────────────────────────────


def test_binding_parity_match_passes() -> None:
    fp = _canonical_fp()
    assert_binding_parity(fp, fp)
    assert_binding_parity(None, None)


def test_binding_parity_mismatch_fails_closed() -> None:
    with pytest.raises(HumanGateAuthorityDrift, match="parity failure"):
        assert_binding_parity("deadbeef", _canonical_fp())
    # A locally claimed exact fingerprint against legacy canonical provenance
    # is drift, not an override.
    with pytest.raises(HumanGateAuthorityDrift, match="parity failure"):
        assert_binding_parity(_canonical_fp(), None)


# ── Item 3: decision persistence ─────────────────────────────────────────────


def test_fingerprint_is_deterministic_and_legacy_is_none() -> None:
    assert _canonical_fp() == _canonical_fp()
    assert _canonical_fp(sha=OTHER_SHA) != _canonical_fp()
    assert (
        binding_fingerprint(
            candidate_sha=None,
            candidate_branch=None,
            baseline_mcp_sha=BASELINE_MCP_SHA,
            baseline_hermes_sha=BASELINE_HERMES_SHA,
            baseline_phase_s_sha=BASELINE_PHASE_S_SHA,
            api_version=API_VERSION,
        )
        is None
    )


def test_decision_body_roundtrip() -> None:
    fp = _canonical_fp()
    body = format_gate_decision_body(
        decision="YES", task_id="t_gate", board="b", reason="evidence complete",
        requester="r", binding_fingerprint=fp,
    )
    assert body.startswith("HUMAN_GATE YES")
    (record,) = parse_recorded_gate_decisions([{"body": body}])
    assert record.decision == "YES"
    assert record.binding_fingerprint == fp


def test_legacy_comment_without_binding_line_never_authorizes() -> None:
    records = parse_recorded_gate_decisions([{"body": "HUMAN_GATE YES: t_gate on b"}])
    assert len(records) == 1
    assert records[0].binding_fingerprint is None
    assert resolve_gate_authority(canonical_fingerprint=_canonical_fp(), decisions=records) == "needs_input"


def test_same_fingerprint_reprepare_preserves_yes() -> None:
    fp = _canonical_fp()
    body = format_gate_decision_body(
        decision="YES", task_id="t_gate", board="b", binding_fingerprint=fp
    )
    records = parse_recorded_gate_decisions([{"body": body}])
    assert resolve_gate_authority(canonical_fingerprint=fp, decisions=records) == "authorized"


def test_same_fingerprint_reprepare_preserves_no_as_denied() -> None:
    fp = _canonical_fp()
    bodies = [
        format_gate_decision_body(decision="YES", task_id="t_gate", board="b", binding_fingerprint=fp),
        format_gate_decision_body(decision="NO", task_id="t_gate", board="b", binding_fingerprint=fp),
    ]
    records = parse_recorded_gate_decisions([{"body": b} for b in bodies])
    assert resolve_gate_authority(canonical_fingerprint=fp, decisions=records) == "denied"


def test_changed_fingerprint_requires_fresh_authority() -> None:
    fp = _canonical_fp()
    body = format_gate_decision_body(
        decision="YES", task_id="t_gate", board="b", binding_fingerprint=fp
    )
    records = parse_recorded_gate_decisions([{"body": body}])
    assert (
        resolve_gate_authority(canonical_fingerprint=_canonical_fp(sha=OTHER_SHA), decisions=records)
        == "needs_input"
    )


def test_never_auto_approves() -> None:
    fp = _canonical_fp()
    assert resolve_gate_authority(canonical_fingerprint=fp, decisions=[]) == "needs_input"
    yes = parse_recorded_gate_decisions(
        [format_gate_decision_body(decision="YES", task_id="t", board="b", binding_fingerprint=fp)]
    )
    # Legacy provenance has no stable identity: even a recorded YES authorizes nothing.
    assert resolve_gate_authority(canonical_fingerprint=None, decisions=yes) == "needs_input"


# ── Item 4: historical shape end to end ──────────────────────────────────────


def test_historical_shape_decision_persists_and_inversion_rejected(
    historical_shape: _FakeRead,
) -> None:
    """Exact binding + YES + same-fingerprint reprepare authorizes; inversion fails."""
    fp = _canonical_fp()
    yes_body = format_gate_decision_body(
        decision="YES",
        task_id="t_gate",
        board="hermes-chatgpt-mcp",
        reason="exact binding verified",
        binding_fingerprint=fp,
    )
    records = parse_recorded_gate_decisions([{"body": yes_body}])
    assert resolve_gate_authority(canonical_fingerprint=fp, decisions=records) == "authorized"
    # Correct direction still flows ...
    assert_human_gate_dag_direction(
        read_adapter=historical_shape, parent_id="t_gate", child_id="t_new"
    )
    # ... while the historical inversion is rejected.
    with pytest.raises(HumanGateDagViolation):
        assert_human_gate_dag_direction(
            read_adapter=historical_shape, parent_id="t_post", child_id="t_gate"
        )
