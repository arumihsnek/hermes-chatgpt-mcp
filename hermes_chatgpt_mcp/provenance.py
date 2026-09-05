# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92 (V4-BASELINE.md §1)
# Candidate: wt/t_78ac0513 — Wave-4 control-plane differential (carries forward W0 contract).
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

BASELINE_BRANCH = "v4/baseline-post-update-885e9ef"
BASELINE_HERMES_SHA = "885e9ef7382930d5eef713fa8bc2e232f7aa4a22"
BASELINE_MCP_SHA = "d7eba25ea8f692d2d0b65d7e5044df79e94c8a92"
BASELINE_PHASE_S_SHA = "ef22b89e8b4955929900b7938ed92cf49411818c"
BASELINE_HERMES_SHORT = BASELINE_HERMES_SHA[:8]
BASELINE_MCP_SHORT = BASELINE_MCP_SHA[:7]
API_VERSION = "v4.wave0"
WAVE = "wave4"


@dataclass(frozen=True)
class V4Baseline:
    branch: str = BASELINE_BRANCH
    hermes_sha: str = BASELINE_HERMES_SHA
    mcp_sha: str = BASELINE_MCP_SHA
    phase_s_sha: str = BASELINE_PHASE_S_SHA
    api_version: str = API_VERSION

    def as_dict(self) -> dict[str, str]:
        return {
            "branch": self.branch,
            "hermes_sha": self.hermes_sha,
            "mcp_sha": self.mcp_sha,
            "phase_s_sha": self.phase_s_sha,
            "api_version": self.api_version,
        }


@dataclass(frozen=True)
class GitCandidateBinding:
    candidate_sha: str
    branch: str
    source_ref: str
    kind: Literal["git"] = "git"

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "candidate_sha": self.candidate_sha,
            "branch": self.branch,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True)
class ReviewBinding:
    task_id: str
    attachment_id: int
    digest: str
    reviewed_candidate_task_id: str
    reviewed_candidate_attachment_id: int
    reviewed_candidate_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "attachment_id": self.attachment_id,
            "digest": self.digest,
            "reviewed_candidate": {
                "task_id": self.reviewed_candidate_task_id,
                "attachment_id": self.reviewed_candidate_attachment_id,
                "digest": self.reviewed_candidate_digest,
            },
        }


@dataclass(frozen=True)
class ArtifactCandidateBinding:
    candidate_task_id: str
    candidate_attachment_id: int
    candidate_digest: str
    source_ref: str
    review: ReviewBinding
    kind: Literal["artifact"] = "artifact"

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "candidate_task_id": self.candidate_task_id,
            "candidate_attachment_id": self.candidate_attachment_id,
            "candidate_digest": self.candidate_digest,
            "source_ref": self.source_ref,
            "review": self.review.as_dict(),
        }


CandidateBinding = GitCandidateBinding | ArtifactCandidateBinding


def candidate_binding_fingerprint(binding: CandidateBinding) -> str:
    """Return the deterministic fingerprint of a canonical verified binding."""
    canonical = json.dumps(binding.as_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateProvenance:
    candidate_sha: str | None
    candidate_branch: str | None
    baseline: V4Baseline
    binding: CandidateBinding | None = None

    @property
    def binding_fingerprint(self) -> str | None:
        return candidate_binding_fingerprint(self.binding) if self.binding is not None else None

    def provenance_header(self, surface: str) -> str:
        if isinstance(self.binding, ArtifactCandidateBinding):
            cand = f"artifact:{self.binding.candidate_digest[:12]}"
        else:
            cand = (self.candidate_sha or "unknown")[:12]
        base = self.baseline.mcp_sha[:7]
        return f"{cand}/{base}/{surface}"

    def as_dict(self, surface: str) -> dict[str, object]:
        return {
            "candidate_sha": self.candidate_sha,
            "candidate_branch": self.candidate_branch,
            "baseline_branch": self.baseline.branch,
            "baseline_hermes_sha": self.baseline.hermes_sha,
            "baseline_mcp_sha": self.baseline.mcp_sha,
            "baseline_phase_s_sha": self.baseline.phase_s_sha,
            "api_version": self.baseline.api_version,
            "surface": surface,
            "provenance_header": self.provenance_header(surface),
            "binding": self.binding.as_dict() if self.binding is not None else None,
            "binding_fingerprint": self.binding_fingerprint,
        }


def _git_head() -> tuple[str | None, str | None]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=2).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, timeout=2).strip()
        if sha and len(sha) >= 7:
            return sha, branch
    except Exception:
        pass
    return None, None


_FULL_SHA = re.compile(r"^[0-9a-f]{7,64}$")
_BRANCH = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")


def _manifest_candidate() -> tuple[str | None, str | None]:
    """Read the identity declared by the running build.

    A deployed service may run from a detached worktree, where Git reports
    ``HEAD`` and can therefore describe the wrong candidate.  Once a build
    manifest or explicit candidate environment is configured, that source is
    authoritative and invalid data fails closed instead of falling back to the
    process working directory.
    """
    manifest_path = os.environ.get("MCP_BUILD_METADATA_FILE", "").strip()
    sha = os.environ.get("MCP_CANDIDATE_SHA", "").strip().lower()
    branch = os.environ.get("MCP_CANDIDATE_BRANCH", "").strip()

    if manifest_path:
        try:
            payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None, None
        if not isinstance(payload, dict):
            return None, None
        declared_sha = payload.get("build_commit")
        if not isinstance(declared_sha, str) or not declared_sha.strip():
            return None, None
        sha = declared_sha.strip().lower()
        declared_branch = payload.get("candidate_branch")
        if isinstance(declared_branch, str) and declared_branch.strip():
            branch = declared_branch.strip()

    if not _FULL_SHA.fullmatch(sha) or not _BRANCH.fullmatch(branch):
        return None, None
    return sha, branch


def get_candidate_provenance(surface: str = "stable") -> CandidateProvenance:
    configured = any(
        os.environ.get(name, "").strip()
        for name in ("MCP_BUILD_METADATA_FILE", "MCP_CANDIDATE_SHA", "MCP_CANDIDATE_BRANCH")
    )
    if configured:
        # Never fall back to an unrelated Git cwd after deployment declares
        # its identity source; that is the exact failure this projection fixes.
        sha, branch = _manifest_candidate()
    else:
        sha, branch = _git_head()
    return CandidateProvenance(candidate_sha=sha, candidate_branch=branch, baseline=V4Baseline())


_EXACT_CANDIDATE_RE = re.compile(r"\bexact\s+candidate\s+([0-9a-f]{40})\b", re.IGNORECASE)
_CANDIDATE_SHA_FIELD_RE = re.compile(r"[\"']candidate_sha[\"']?\s*[:=]\s*[\"']([0-9a-f]{40})[\"']", re.IGNORECASE)
_BRANCH_RE = re.compile(r"\bon\s+branch\s+([A-Za-z0-9._/-]{1,128})\b", re.IGNORECASE)
_CANDIDATE_BRANCH_FIELD_RE = re.compile(
    r"[\"']candidate_branch[\"']?\s*[:=]\s*[\"']([^\"'\s,]{1,128})[\"']",
    re.IGNORECASE,
)
_GIT_DECLARATION_MARKER_RE = re.compile(
    r"\bexact\s+candidate\s+(?!(?:binding)\b)|"
    r"[\"']candidate_sha[\"']?\s*[:=]|"
    r"[\"']candidate_branch[\"']?\s*[:=]|"
    r"\bon\s+branch\b",
    re.IGNORECASE,
)
_ARTIFACT_DECLARATION_MARKER_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?(?:"
    r"EXACT CANDIDATE BINDING|Candidate task:|Candidate attachment:|Candidate SHA-256:|"
    r"INDEPENDENT REVIEW BINDING|Review task:|Review report attachment:|Review report SHA-256:)",
)
_TASK_ID_RE = r"t_[A-Za-z0-9_-]+"
_ARTIFACT_CANDIDATE_TASK_RE = re.compile(
    rf"(?im)^[ \t]*(?:[-*][ \t]*)?Candidate task:[ \t]*({_TASK_ID_RE})[ \t]*$"
)
_ARTIFACT_CANDIDATE_ATTACHMENT_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?Candidate attachment:[ \t]*"
    r"(\d+)(?:[ \t]+`([^`\r\n]+)`)?[ \t]*$"
)
_ARTIFACT_CANDIDATE_DIGEST_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?Candidate SHA-256:[ \t]*([0-9a-f]{64})[ \t]*$"
)
_ARTIFACT_REVIEW_TASK_RE = re.compile(
    rf"(?im)^[ \t]*(?:[-*][ \t]*)?Review task:[ \t]*({_TASK_ID_RE})[ \t]*$"
)
_ARTIFACT_REVIEW_ATTACHMENT_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?Review report attachment:[ \t]*"
    r"(\d+)(?:[ \t]+`([^`\r\n]+)`)?[ \t]*$"
)
_ARTIFACT_REVIEW_DIGEST_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?Review report SHA-256:[ \t]*([0-9a-f]{64})[ \t]*$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def extract_exact_candidate_from_task_body(body: str) -> tuple[str | None, str | None]:
    """Extract an explicit exact candidate declaration from a task body.

    This intentionally ignores vague references such as short SHAs or prose like
    "candidate build". Human-gate binding requires a full SHA and explicit branch.
    """
    if not body:
        return None, None
    sha_match = _EXACT_CANDIDATE_RE.search(body) or _CANDIDATE_SHA_FIELD_RE.search(body)
    branch_match = _BRANCH_RE.search(body) or _CANDIDATE_BRANCH_FIELD_RE.search(body)
    sha = sha_match.group(1).lower() if sha_match else None
    branch = branch_match.group(1) if branch_match else None
    return sha, branch


def _verify_remote_candidate(sha: str, branch: str, remote_name: str = "origin") -> bool:
    """Verify the declared branch resolves to the exact candidate SHA remotely."""
    try:
        output = subprocess.check_output(
            ["git", "ls-remote", remote_name, f"refs/heads/{branch}"],
            text=True,
            timeout=5,
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False
    if not output:
        return False
    remote_sha = output.split()[0].lower()
    return remote_sha == sha.lower()


def _artifact_field_matches(body: str) -> dict[str, re.Match[str] | None]:
    return {
        "candidate_task": _ARTIFACT_CANDIDATE_TASK_RE.search(body),
        "candidate_attachment": _ARTIFACT_CANDIDATE_ATTACHMENT_RE.search(body),
        "candidate_digest": _ARTIFACT_CANDIDATE_DIGEST_RE.search(body),
        "review_task": _ARTIFACT_REVIEW_TASK_RE.search(body),
        "review_attachment": _ARTIFACT_REVIEW_ATTACHMENT_RE.search(body),
        "review_digest": _ARTIFACT_REVIEW_DIGEST_RE.search(body),
    }


def _read_verified_attachment(
    attachment_reader: Callable[[str, int], bytes],
    *,
    task_id: str,
    attachment_id: int,
    label: str,
) -> bytes:
    try:
        data = attachment_reader(task_id, attachment_id)
    except Exception as exc:
        raise ValueError(f"{label} could not be read from the authoritative attachment surface") from exc
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError(f"{label} could not be verified: attachment reader returned invalid bytes")
    return bytes(data)


def _verify_review_report_binding(report: bytes, binding: ArtifactCandidateBinding) -> None:
    try:
        text = report.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("review artifact could not be verified: report is not UTF-8") from exc
    if binding.candidate_digest not in text:
        raise ValueError("review report does not bind the exact candidate digest")
    if binding.candidate_task_id not in text:
        raise ValueError("review report does not bind the exact candidate task")
    attachment_pattern = rf"\battachment(?:[ \t]+id)?[ \t]*{binding.candidate_attachment_id}\b"
    if re.search(attachment_pattern, text, re.IGNORECASE) is None:
        raise ValueError("review report does not bind the exact candidate attachment")


def _bind_artifact_candidate(
    body: str,
    *,
    task_reader: Callable[[str], Any] | None,
    attachment_reader: Callable[[str, int], bytes] | None,
) -> CandidateProvenance:
    fields = _artifact_field_matches(body)
    if any(match is None for match in fields.values()):
        raise ValueError("task artifact-candidate declaration is incomplete")
    candidate_task_match = fields["candidate_task"]
    candidate_attachment_match = fields["candidate_attachment"]
    candidate_digest_match = fields["candidate_digest"]
    review_task_match = fields["review_task"]
    review_attachment_match = fields["review_attachment"]
    review_digest_match = fields["review_digest"]
    assert candidate_task_match and candidate_attachment_match and candidate_digest_match
    assert review_task_match and review_attachment_match and review_digest_match

    candidate_task_id = candidate_task_match.group(1)
    candidate_attachment_id = int(candidate_attachment_match.group(1))
    candidate_digest = candidate_digest_match.group(1).lower()
    review_task_id = review_task_match.group(1)
    review_attachment_id = int(review_attachment_match.group(1))
    review_digest = review_digest_match.group(1).lower()
    if (
        candidate_attachment_id < 1
        or review_attachment_id < 1
        or not _SHA256.fullmatch(candidate_digest)
        or not _SHA256.fullmatch(review_digest)
    ):
        raise ValueError("task artifact-candidate declaration is invalid")
    if task_reader is None or attachment_reader is None:
        raise ValueError("artifact candidate cannot be verified without the authoritative read surface")

    try:
        candidate_task = task_reader(candidate_task_id)
        review_task = task_reader(review_task_id)
    except Exception as exc:
        raise ValueError("artifact candidate task or review task could not be read") from exc
    if candidate_task is None or str(getattr(candidate_task, "id", "")) != candidate_task_id:
        raise ValueError("candidate task identity could not be verified")
    if review_task is None or str(getattr(review_task, "id", "")) != review_task_id:
        raise ValueError("review task identity could not be verified")
    review_status = str(getattr(review_task, "status", "")).strip().lower()
    if review_status != "done":
        raise ValueError("review task is not complete")
    review_summary = " ".join(
        str(getattr(review_task, field, "") or "") for field in ("result", "latest_summary")
    )
    if re.search(r"\bPASS\b", review_summary, re.IGNORECASE) is None:
        raise ValueError("review task does not have a PASS result")

    candidate_bytes = _read_verified_attachment(
        attachment_reader,
        task_id=candidate_task_id,
        attachment_id=candidate_attachment_id,
        label="candidate artifact",
    )
    if hashlib.sha256(candidate_bytes).hexdigest() != candidate_digest:
        raise ValueError("candidate artifact digest does not match the declaration")
    review_bytes = _read_verified_attachment(
        attachment_reader,
        task_id=review_task_id,
        attachment_id=review_attachment_id,
        label="review artifact",
    )
    if hashlib.sha256(review_bytes).hexdigest() != review_digest:
        raise ValueError("review artifact digest does not match the declaration")

    binding = ArtifactCandidateBinding(
        candidate_task_id=candidate_task_id,
        candidate_attachment_id=candidate_attachment_id,
        candidate_digest=candidate_digest,
        source_ref=f"task:{candidate_task_id}/attachment:{candidate_attachment_id}",
        review=ReviewBinding(
            task_id=review_task_id,
            attachment_id=review_attachment_id,
            digest=review_digest,
            reviewed_candidate_task_id=candidate_task_id,
            reviewed_candidate_attachment_id=candidate_attachment_id,
            reviewed_candidate_digest=candidate_digest,
        ),
    )
    _verify_review_report_binding(review_bytes, binding)
    return CandidateProvenance(candidate_sha=None, candidate_branch=None, baseline=V4Baseline(), binding=binding)


def bind_candidate_provenance_to_task(
    body: str,
    *,
    remote_name: str = "origin",
    task_reader: Callable[[str], Any] | None = None,
    attachment_reader: Callable[[str, int], bytes] | None = None,
) -> CandidateProvenance | None:
    """Return task-bound provenance or fail closed for an invalid declaration.

    A task with no candidate declaration may use the normal running-build
    provenance. An explicit Git declaration requires a full SHA, branch, and
    remote identity match. An explicit artifact declaration requires exact
    candidate and review bindings verified through the read adapter. Any
    invalid declaration fails closed; no Human Gate may use running-build
    provenance in that case.
    """
    artifact_declared = _ARTIFACT_DECLARATION_MARKER_RE.search(body or "") is not None
    git_declared = _GIT_DECLARATION_MARKER_RE.search(body or "") is not None
    if artifact_declared:
        if git_declared:
            raise ValueError("task candidate declaration contains multiple candidate types")
        return _bind_artifact_candidate(
            body,
            task_reader=task_reader,
            attachment_reader=attachment_reader,
        )

    sha, branch = extract_exact_candidate_from_task_body(body)
    if sha is None and branch is None:
        if git_declared:
            raise ValueError("task exact-candidate declaration is incomplete")
        return None
    if sha is None or branch is None:
        raise ValueError("task exact-candidate declaration is incomplete")
    if not _FULL_SHA.fullmatch(sha) or not _BRANCH.fullmatch(branch):
        raise ValueError("task exact-candidate declaration is invalid")
    if not _verify_remote_candidate(sha, branch, remote_name=remote_name):
        raise ValueError("task exact candidate could not be verified against remote branch")
    return CandidateProvenance(
        candidate_sha=sha,
        candidate_branch=branch,
        baseline=V4Baseline(),
        binding=GitCandidateBinding(candidate_sha=sha, branch=branch, source_ref=f"refs/heads/{branch}"),
    )


def get_baseline() -> V4Baseline:
    return V4Baseline()
