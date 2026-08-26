# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92 (V4-BASELINE.md §1)
# Candidate: wt/t_78ac0513 — Wave-4 control-plane differential (carries forward W0 contract).
from __future__ import annotations

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


def get_candidate_provenance(surface: str = "stable") -> CandidateProvenance:
    sha, branch = _git_head()
    return CandidateProvenance(candidate_sha=sha, candidate_branch=branch, baseline=V4Baseline())


def get_baseline() -> V4Baseline:
    return V4Baseline()
