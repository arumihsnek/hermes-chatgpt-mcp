from __future__ import annotations

from types import SimpleNamespace

import pytest

from hermes_chatgpt_mcp import provenance
from hermes_chatgpt_mcp.control_plane import build_gate_context


CANDIDATE_SHA = "db9bebaee149b07e707fef66c33b8c05ced48766"
CANDIDATE_BRANCH = "mcp-ui-interactive-r1"


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


def test_gate_context_without_task_candidate_preserves_manifest_identity(tmp_path, monkeypatch):
    build_sha = "ff15b65fcd5ef6eb9a5dafeecd3c3b1d646607b8"
    metadata = tmp_path / "build.json"
    metadata.write_text(
        '{"build_commit":"' + build_sha + '","candidate_branch":"mcp-ui-forwardport-r2"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("MCP_BUILD_METADATA_FILE", str(metadata))
    ctx = build_gate_context(
        read_adapter=_ReadAdapter("No exact candidate declaration here."),
        board="hermes-chatgpt-mcp",
        task_id="t_gate",
        surface="beta",
    )
    assert ctx.provenance.candidate_sha == build_sha
    assert ctx.provenance.candidate_branch == "mcp-ui-forwardport-r2"
