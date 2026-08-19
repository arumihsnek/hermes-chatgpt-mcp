from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_chatgpt_mcp.config import Settings
from hermes_chatgpt_mcp.release import BuildMetadataError, load_build_metadata


def test_missing_release_manifest_returns_empty_metadata(tmp_path: Path):
    metadata = load_build_metadata(tmp_path / "missing.json")

    assert metadata.public_dict() == {
        "build_commit": None,
        "surface": None,
        "deployed_at": None,
    }


def test_settings_reads_release_manifest_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCP_OAUTH_USERNAME", "chatgpt")
    monkeypatch.setenv("MCP_OAUTH_PASSWORD", "correct horse battery staple")
    monkeypatch.setenv("MCP_OAUTH_SIGNING_KEY", "k" * 48)
    monkeypatch.setenv("MCP_BUILD_METADATA_FILE", str(tmp_path / "build.json"))

    settings = Settings.from_env()

    assert settings.build_metadata_file == tmp_path / "build.json"


def test_valid_release_manifest_has_only_public_fields(tmp_path: Path):
    manifest = tmp_path / "build.json"
    manifest.write_text(
        json.dumps(
            {
                "build_commit": "a" * 40,
                "surface": "beta",
                "deployed_at": "2026-08-19T12:00:00Z",
                "metadata_path": "/var/lib/private/build.json",
                "token": "must-not-leak",
            }
        ),
        encoding="utf-8",
    )

    metadata = load_build_metadata(manifest)

    assert metadata.public_dict() == {
        "build_commit": "a" * 40,
        "surface": "beta",
        "deployed_at": "2026-08-19T12:00:00Z",
    }


@pytest.mark.parametrize(
    "payload",
    ["not-json", "[]", '{"build_commit": 42}', '{"surface": "production"}'],
)
def test_invalid_release_manifest_fails_closed_without_echoing_contents(tmp_path: Path, payload: str):
    manifest = tmp_path / "build.json"
    manifest.write_text(payload, encoding="utf-8")

    with pytest.raises(BuildMetadataError) as error:
        load_build_metadata(manifest)

    assert "must-not-leak" not in str(error.value)
