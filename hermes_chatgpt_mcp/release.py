from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .provenance import API_VERSION, get_baseline


class BuildMetadataError(ValueError):
    """Raised when a configured release manifest is not safe to consume."""


_COMMIT_RE = re.compile(r"^[0-9a-f]{7,64}$")
_TEXT_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")
_SURFACES = frozenset({"stable", "beta"})


@dataclass(frozen=True)
class BuildMetadata:
    build_commit: str | None = None
    surface: str | None = None
    deployed_at: str | None = None

    def public_dict(self) -> dict[str, str | None]:
        """Return the deliberately small public release projection."""

        return {
            "build_commit": self.build_commit,
            "surface": self.surface,
            "deployed_at": self.deployed_at,
        }


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not _TEXT_RE.fullmatch(value):
        raise BuildMetadataError(f"invalid release metadata field: {key}")
    return value


def load_build_metadata(path: Path | None) -> BuildMetadata:
    """Load a configured manifest without exposing arbitrary manifest fields."""

    if path is None or not path.exists():
        return BuildMetadata()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BuildMetadataError("invalid release metadata") from exc
    if not isinstance(payload, dict):
        raise BuildMetadataError("invalid release metadata")

    commit = _required_text(payload, "build_commit")
    if not _COMMIT_RE.fullmatch(commit):
        raise BuildMetadataError("invalid release metadata field: build_commit")
    surface = _required_text(payload, "surface")
    if surface not in _SURFACES:
        raise BuildMetadataError("invalid release metadata field: surface")
    deployed_at = _required_text(payload, "deployed_at")
    return BuildMetadata(build_commit=commit, surface=surface, deployed_at=deployed_at)


def canary_manifest(*, build_commit: str, surface: str, deployed_at: str) -> dict[str, str]:
    """Build a detached canary manifest payload validated against the frozen baseline contract."""

    if not _COMMIT_RE.fullmatch(build_commit):
        raise BuildMetadataError("invalid release metadata field: build_commit")
    if surface not in _SURFACES:
        raise BuildMetadataError("invalid release metadata field: surface")
    baseline = get_baseline()
    return {
        "build_commit": build_commit,
        "surface": surface,
        "deployed_at": deployed_at,
        "api_version": baseline.api_version,
        "baseline_branch": baseline.branch,
        "baseline_mcp_sha": baseline.mcp_sha,
    }
