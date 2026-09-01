from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from hermes_chatgpt_mcp import control_plane, provenance
from hermes_chatgpt_mcp.control_plane import build_gate_context, revalidate_gate_context


CANDIDATE_SHA = "db9bebaee149b07e707fef66c33b8c05ced48766"
CANDIDATE_BRANCH = "mcp-ui-interactive-r1"
ARTIFACT_TASK_ID = "t_candidate"
ARTIFACT_ATTACHMENT_ID = 877
REVIEW_TASK_ID = "t_review"
REVIEW_ATTACHMENT_ID = 878
ARTIFACT_BYTES = b"candidate artifact bytes\n"
ARTIFACT_DIGEST = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
REVIEW_BYTES = (
    f"**Candidate SHA-256:** {ARTIFACT_DIGEST}\n"
    f"**Parent Task:** {ARTIFACT_TASK_ID} (attachment id {ARTIFACT_ATTACHMENT_ID})\n"
).encode()
REVIEW_DIGEST = hashlib.sha256(REVIEW_BYTES).hexdigest()


class _ReadAdapter:
    def __init__(self, body: str) -> None:
        self.task = SimpleNamespace(
            id="t_gate",
            title="gate",
            status="blocked",
            body=body,
            latest_summary=None,
            result=None,
            parent_ids=[],
            child_ids=[],
        )

    def get_task(self, task_id: str):
        assert task_id == "t_gate"
        return self.task

    def get_activity(self, task_id: str, *, max_items: int, log_bytes: int):
        return SimpleNamespace(truncated=False)

    def get_dispatch(self, task_id: str):
        return SimpleNamespace(state="BLOCKED", reasons=["needs_input"])


def _artifact_body(
    *,
    candidate_digest: str = ARTIFACT_DIGEST,
    review_digest: str = REVIEW_DIGEST,
) -> str:
    return f"""CORE HUMAN GATE — ARTIFACT CANDIDATE

EXACT CANDIDATE BINDING
- Candidate task: {ARTIFACT_TASK_ID}
- Candidate attachment: {ARTIFACT_ATTACHMENT_ID} `C2-CONDUCTOR-SYNC-CANDIDATE.md`
- Candidate SHA-256: {candidate_digest}

INDEPENDENT REVIEW BINDING
- Review task: {REVIEW_TASK_ID}
- Verdict: PASS — exact-byte review
- Review report attachment: {REVIEW_ATTACHMENT_ID} `C2-REVIEW-REPORT.md`
- Review report SHA-256: {review_digest}
"""


class _ArtifactReadAdapter(_ReadAdapter):
    def __init__(self, body: str, *, review_bytes: bytes = REVIEW_BYTES) -> None:
        super().__init__(body)
        self.tasks = {
            "t_gate": self.task,
            ARTIFACT_TASK_ID: SimpleNamespace(
                id=ARTIFACT_TASK_ID,
                title="C2 candidate",
                status="done",
                body="candidate task",
                latest_summary="C2 candidate persisted",
                result="PASS",
                parent_ids=[],
                child_ids=[],
            ),
            REVIEW_TASK_ID: SimpleNamespace(
                id=REVIEW_TASK_ID,
                title="C2 review",
                status="done",
                body="independent review",
                latest_summary="PASS — exact-byte review",
                result="PASS — 13/13",
                parent_ids=[ARTIFACT_TASK_ID],
                child_ids=[],
            ),
        }
        self.attachments = {
            (ARTIFACT_TASK_ID, ARTIFACT_ATTACHMENT_ID): ARTIFACT_BYTES,
            (REVIEW_TASK_ID, REVIEW_ATTACHMENT_ID): review_bytes,
        }

    def get_task(self, task_id: str):
        return self.tasks[task_id]

    def read_attachment_bytes(self, task_id: str, attachment_id: int) -> bytes:
        return self.attachments[(task_id, attachment_id)]


def test_extracts_explicit_exact_candidate_and_branch():
    body = f"Activate exact candidate {CANDIDATE_SHA} on branch {CANDIDATE_BRANCH}."
    assert provenance.extract_exact_candidate_from_task_body(body) == (
        CANDIDATE_SHA,
        CANDIDATE_BRANCH,
    )


def test_remote_mismatch_fails_closed(monkeypatch):
    body = f"Activate exact candidate {CANDIDATE_SHA} on branch {CANDIDATE_BRANCH}."
    monkeypatch.setattr(provenance, "_verify_remote_candidate", lambda sha, branch, remote_name="origin": False)
    with pytest.raises(ValueError, match="could not be verified"):
        provenance.bind_candidate_provenance_to_task(body)


def test_partial_explicit_declaration_fails_closed():
    with pytest.raises(ValueError, match="incomplete"):
        provenance.bind_candidate_provenance_to_task(f"Activate exact candidate {CANDIDATE_SHA}.")

    with pytest.raises(ValueError, match="incomplete"):
        provenance.bind_candidate_provenance_to_task("This is an exact candidate declaration.")


def test_branch_only_git_declaration_fails_closed():
    with pytest.raises(ValueError, match="incomplete"):
        provenance.bind_candidate_provenance_to_task(f"Use the candidate on branch {CANDIDATE_BRANCH}.")


def test_gate_context_uses_verified_task_candidate(monkeypatch):
    body = f"Activate exact candidate {CANDIDATE_SHA} on branch {CANDIDATE_BRANCH}."
    monkeypatch.setattr(provenance, "_verify_remote_candidate", lambda sha, branch, remote_name="origin": True)
    ctx = build_gate_context(
        read_adapter=_ReadAdapter(body),
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    assert ctx.provenance.candidate_sha == CANDIDATE_SHA
    assert ctx.provenance.candidate_branch == CANDIDATE_BRANCH
    assert ctx.provenance.provenance_header.startswith(CANDIDATE_SHA[:12])
    assert ctx.provenance.binding is not None
    assert ctx.provenance.binding.kind == "git"


def test_gate_context_without_task_candidate_preserves_manifest_identity(tmp_path, monkeypatch):
    build_sha = "ff15b65fcd5ef6eb9a5dafeecd3c3b1d646607b8"
    metadata = tmp_path / "build.json"
    metadata.write_text(
        '{"build_commit":"' + build_sha + '","candidate_branch":"mcp-ui-forwardport-r2"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("MCP_BUILD_METADATA_FILE", str(metadata))
    ctx = build_gate_context(
        read_adapter=_ReadAdapter("No candidate is declared here."),
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    assert ctx.provenance.candidate_sha == build_sha
    assert ctx.provenance.candidate_branch == "mcp-ui-forwardport-r2"


def test_artifact_candidate_binds_exact_candidate_and_review_without_running_build(monkeypatch):
    build_sha = "f" * 40
    monkeypatch.setenv("MCP_CANDIDATE_SHA", build_sha)
    adapter = _ArtifactReadAdapter(_artifact_body())

    ctx = build_gate_context(
        read_adapter=adapter,
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )

    binding = ctx.provenance.binding
    assert binding is not None
    assert binding.kind == "artifact"
    assert binding.candidate_task_id == ARTIFACT_TASK_ID
    assert binding.candidate_attachment_id == ARTIFACT_ATTACHMENT_ID
    assert binding.candidate_digest == ARTIFACT_DIGEST
    assert binding.review.task_id == REVIEW_TASK_ID
    assert binding.review.attachment_id == REVIEW_ATTACHMENT_ID
    assert binding.review.digest == REVIEW_DIGEST
    assert ctx.provenance.candidate_sha is None
    assert ctx.provenance.provenance_header.startswith(f"artifact:{ARTIFACT_DIGEST[:12]}")
    assert build_sha not in format(ctx.provenance.provenance_header)
    markdown = control_plane.format_gate_markdown(ctx)
    assert ARTIFACT_TASK_ID in markdown
    assert str(ARTIFACT_ATTACHMENT_ID) in markdown
    assert ARTIFACT_DIGEST in markdown
    assert REVIEW_TASK_ID in markdown
    assert REVIEW_DIGEST in markdown
    assert build_sha not in markdown
    assert ctx.provenance.binding_fingerprint


def test_artifact_filename_is_not_candidate_identity():
    first = build_gate_context(
        read_adapter=_ArtifactReadAdapter(_artifact_body()),
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    renamed = _artifact_body().replace("C2-CONDUCTOR-SYNC-CANDIDATE.md", "renamed-title.md")
    second = build_gate_context(
        read_adapter=_ArtifactReadAdapter(renamed),
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    assert first.provenance.binding_fingerprint == second.provenance.binding_fingerprint


def test_explicit_incomplete_artifact_declaration_fails_closed_without_build_fallback(monkeypatch):
    monkeypatch.setattr(
        control_plane,
        "provenance_bundle",
        lambda surface: pytest.fail("running-build provenance must not be used"),
    )
    adapter = _ArtifactReadAdapter(
        "EXACT CANDIDATE BINDING\n- Candidate task: t_candidate\n"
    )

    with pytest.raises(ValueError, match="incomplete"):
        build_gate_context(
            read_adapter=adapter,
            board="hermes-chatgpt-mcp",
            task_id="t_gate",
            surface="beta",
        )


def test_wrong_artifact_digest_fails_closed(monkeypatch):
    monkeypatch.setattr(
        control_plane,
        "provenance_bundle",
        lambda surface: pytest.fail("running-build provenance must not be used"),
    )
    adapter = _ArtifactReadAdapter(_artifact_body(candidate_digest="0" * 64))

    with pytest.raises(ValueError, match="candidate artifact digest"):
        build_gate_context(
            read_adapter=adapter,
            board="hermes-chatgpt-mcp",
            task_id="t_gate",
            surface="beta",
        )


def test_review_report_must_bind_the_exact_candidate(monkeypatch):
    wrong_review = (
        f"**Candidate SHA-256:** {'1' * 64}\n"
        f"**Parent Task:** t_other (attachment id {ARTIFACT_ATTACHMENT_ID})\n"
    ).encode()
    adapter = _ArtifactReadAdapter(
        _artifact_body(review_digest=hashlib.sha256(wrong_review).hexdigest()),
        review_bytes=wrong_review,
    )

    with pytest.raises(ValueError, match="review.*candidate"):
        build_gate_context(
            read_adapter=adapter,
            board="hermes-chatgpt-mcp",
            task_id="t_gate",
            surface="beta",
        )


def test_wrong_review_digest_fails_closed(monkeypatch):
    adapter = _ArtifactReadAdapter(_artifact_body(review_digest="0" * 64))

    with pytest.raises(ValueError, match="review artifact digest"):
        build_gate_context(
            read_adapter=adapter,
            board="hermes-chatgpt-mcp",
            task_id="t_gate",
            surface="beta",
        )


def test_artifact_change_invalidates_prepared_gate(monkeypatch):
    adapter = _ArtifactReadAdapter(_artifact_body())
    prepared = build_gate_context(
        read_adapter=adapter,
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    assert prepared.provenance.binding_fingerprint
    adapter.attachments[(ARTIFACT_TASK_ID, ARTIFACT_ATTACHMENT_ID)] = b"changed candidate bytes\n"

    with pytest.raises(ValueError, match="candidate artifact digest"):
        build_gate_context(
            read_adapter=adapter,
            board="hermes-chatgpt-mcp",
            task_id="t_gate",
            surface="beta",
        )


def test_decision_revalidation_requires_the_prepared_binding_fingerprint():
    adapter = _ArtifactReadAdapter(_artifact_body())
    prepared = build_gate_context(
        read_adapter=adapter,
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    fingerprint = prepared.provenance.binding_fingerprint
    assert fingerprint

    with pytest.raises(ValueError, match="binding fingerprint"):
        revalidate_gate_context(
            read_adapter=adapter,
            board="hermes-chatgpt-mcp",
            task_id="t_gate",
            surface="beta",
            expected_binding_fingerprint="0" * 64,
        )

    revalidated = revalidate_gate_context(
        read_adapter=adapter,
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
        expected_binding_fingerprint=fingerprint,
    )
    assert revalidated.provenance.binding_fingerprint == fingerprint
