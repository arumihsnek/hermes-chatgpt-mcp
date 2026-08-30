# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92 (V4-BASELINE.md §1)
# Candidate: wt/t_78ac0513 — Wave-4 control-plane differential (carries forward W0 contract).
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

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
class CandidateProvenance:
    candidate_sha: str | None
    candidate_branch: str | None
    baseline: V4Baseline

    def provenance_header(self, surface: str) -> str:
        cand = (self.candidate_sha or "unknown")[:12]
        base = self.baseline.mcp_sha[:7]
        return f"{cand}/{base}/{surface}"

    def as_dict(self, surface: str) -> dict[str, str | None]:
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
_CANDIDATE_BRANCH_FIELD_RE = re.compile(r"[\"']candidate_branch[\"']?\s*[:=]\s*[\"']([^\"'\s,]{1,128})[\"']", re.IGNORECASE)


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


def bind_candidate_provenance_to_task(
    body: str,
    *,
    remote_name: str = "origin",
) -> CandidateProvenance | None:
    """Return task-bound provenance or fail closed for an invalid declaration.

    A task with no exact-candidate declaration may use the normal running-build
    provenance. Once either exact SHA or branch is declared, both are mandatory
    and remote identity must match exactly; otherwise no Human Gate may be built.
    """
    sha, branch = extract_exact_candidate_from_task_body(body)
    if sha is None and branch is None:
        return None
    if sha is None or branch is None:
        raise ValueError("task exact-candidate declaration is incomplete")
    if not _FULL_SHA.fullmatch(sha) or not _BRANCH.fullmatch(branch):
        raise ValueError("task exact-candidate declaration is invalid")
    if not _verify_remote_candidate(sha, branch, remote_name=remote_name):
        raise ValueError("task exact candidate could not be verified against remote branch")
    return CandidateProvenance(candidate_sha=sha, candidate_branch=branch, baseline=V4Baseline())


def get_baseline() -> V4Baseline:
    return V4Baseline()
