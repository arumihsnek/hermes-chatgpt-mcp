# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef7382930d5eef713fa8bc2e232f7aa4a22 + d7eba25ea8f692d2d0b65d7e5044df79e94c8a92
# Candidate: wt/t_261a7674 — Wave 0 additive helpers, no baseline mutation.
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .provenance import API_VERSION, get_baseline


COMMIT_RE = re.compile(r"^[0-9a-f]{7,64}$")
SURFACES = frozenset({"stable", "beta"})


def validate_api_version(value: str | None) -> str | None:
    if value is None:
        return None
    if value != API_VERSION and value != "v4":
        raise ValueError(f"unsupported API version: {value!r} (expected {API_VERSION})")
    return value


def validate_provenance_header(value: str | None) -> bool:
    if value is None or not value:
        return False
    parts = value.split("/")
    return len(parts) == 3 and all(p for p in parts)


def canary_manifest(path: Path, *, build_commit: str, surface: str, deployed_at: str) -> dict[str, str]:
    if not COMMIT_RE.fullmatch(build_commit):
        raise ValueError("invalid build_commit")
    if surface not in SURFACES:
        raise ValueError("invalid surface")
    baseline = get_baseline()
    payload = {
        "build_commit": build_commit,
        "surface": surface,
        "deployed_at": deployed_at,
        "api_version": baseline.api_version,
        "baseline_branch": baseline.branch,
        "baseline_mcp_sha": baseline.mcp_sha,
    }
    # Validate JSON serializable before write
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    # Caller writes atomically; here we just validate and return
    _ = json.loads(text)
    return payload


@dataclass(frozen=True)
class AuthIntrospection:
    scopes: tuple[str, ...]
    granted_board: str | None
    board_access: str | None
    surface: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "scopes": list(self.scopes),
            "granted_board": self.granted_board,
            "board_access": self.board_access,
            "surface": self.surface,
            "api_version": API_VERSION,
        }
