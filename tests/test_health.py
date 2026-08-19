from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import httpx

from hermes_chatgpt_mcp.auth import AuthService
from hermes_chatgpt_mcp.boards import HermesBoardResolver
from hermes_chatgpt_mcp.server import create_app
from hermes_cli import kanban_db

from .fixtures import make_hermes_fixture
from .test_auth import _settings


def test_healthz_includes_public_beta_build_metadata(tmp_path: Path, monkeypatch):
    asyncio.run(_test_healthz_includes_public_beta_build_metadata(tmp_path, monkeypatch))


async def _test_healthz_includes_public_beta_build_metadata(tmp_path: Path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(fixture.root))
    metadata_file = tmp_path / "build.json"
    metadata_file.write_text(
        json.dumps(
            {
                "build_commit": "b" * 40,
                "surface": "beta",
                "deployed_at": "2026-08-19T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    settings = replace(
        _settings(),
        hermes_kanban_home=fixture.root,
        default_board=fixture.board,
        surface="beta",
        build_metadata_file=metadata_file,
    )
    auth = AuthService(settings)
    resolver = HermesBoardResolver(settings, hermes_module=kanban_db)
    app = create_app(board_resolver=resolver, settings=settings, auth_service=auth, surface="beta")

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            response = await client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["build"] == {
        "build_commit": "b" * 40,
        "surface": "beta",
        "deployed_at": "2026-08-19T12:00:00Z",
    }
    serialized = json.dumps(body)
    for forbidden in ("metadata_file", "token", "secret", str(metadata_file)):
        assert forbidden not in serialized
