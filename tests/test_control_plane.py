from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.control_plane import (
    DELIVERY_MODES,
    bounded_notify_list,
    build_canary_bundle,
    build_gate_context,
    format_gate_markdown,
    pause_status,
    provenance_bundle,
    validate_delivery_mode,
    validate_gate_actor,
    verify_canary_manifest,
)
from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.provenance import API_VERSION, BASELINE_MCP_SHA

from hermes_cli import kanban_db

from .fixtures import make_hermes_fixture
from .test_auth import _settings  # noqa: F401  (re-exported convention)
from .test_beta_integration import _assert_error, _assert_success, _beta_fixture, _rpc, _token


def _read_adapter(fixture) -> HermesReadOnlyAdapter:
    store = ReadOnlyHermesStore(
        db_path=fixture.db_path,
        board=fixture.board,
        hermes_module=kanban_db,
        hermes_agent_root=fixture.root,
        log_root=fixture.root / "kanban" / "boards" / fixture.board / "logs",
    )
    return HermesReadOnlyAdapter(store)


def test_canary_bundle_roundtrip_carries_baseline_contract():
    bundle = build_canary_bundle(
        build_commit="a" * 40, surface="beta", deployed_at="2026-08-26T00:00:00Z"
    )
    assert bundle.verified is True
    assert bundle.errors == ()
    assert bundle.manifest["api_version"] == API_VERSION == "v4.wave0"
    assert bundle.manifest["baseline_mcp_sha"] == BASELINE_MCP_SHA
    assert bundle.manifest["build_commit"] == "a" * 40

    verified = verify_canary_manifest(dict(bundle.manifest))
    assert verified.verified is True

    tampered = dict(bundle.manifest, api_version="v9")
    rejected = verify_canary_manifest(tampered)
    assert rejected.verified is False
    assert rejected.manifest == {}
    assert rejected.errors


def test_canary_bundle_rejects_invalid_fields():
    for kwargs in (
        {"build_commit": "NOT-A-SHA", "surface": "beta", "deployed_at": "t"},
        {"build_commit": "a" * 40, "surface": "gamma", "deployed_at": "t"},
    ):
        bundle = build_canary_bundle(**kwargs)
        assert bundle.verified is False
        assert bundle.manifest == {}
        assert bundle.errors


def test_gate_actor_self_approval_is_structurally_rejected():
    with pytest.raises(ValueError, match="self-approval"):
        validate_gate_actor(requester="worker-1", actor=" worker-1 ")
    # Unknown actors (offline harnesses) cannot be compared; audit trail still
    # distinguishes the two events.
    validate_gate_actor(requester=None, actor=None)
    validate_gate_actor(requester="worker-1", actor="reviewer")


def test_delivery_mode_validation_is_closed():
    assert validate_delivery_mode(None) is None
    for mode in sorted(DELIVERY_MODES):
        assert validate_delivery_mode(mode) == mode
    with pytest.raises(ValueError, match="unsupported delivery mode"):
        validate_delivery_mode("forever")


def test_bounded_notify_list_enforces_page_bound():
    class Adapter:
        def __init__(self) -> None:
            self.seen: tuple[int, str | None] | None = None

        def notify_list(self, limit, task_id=None):
            self.seen = (limit, task_id)
            return [{"task_id": "review-task"}]

    adapter = Adapter()
    assert bounded_notify_list(manage_adapter=adapter, limit=500) == [{"task_id": "review-task"}]
    assert adapter.seen == (500, None)
    for bad_limit in (0, 1001):
        with pytest.raises(ValueError, match="limit"):
            bounded_notify_list(manage_adapter=adapter, limit=bad_limit)


def test_pause_status_reads_sentinel_without_mutating_it(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    sentinel = tmp_path / "ESTOP"

    before = pause_status()
    assert before["paused"] is False
    assert before["status"] != "unknown" if "status" in before else True
    assert not sentinel.exists()

    sentinel.write_text("operator stop\n", encoding="utf-8")
    after = pause_status()
    assert after["paused"] is True
    assert after["detail"].startswith("operator stop")
    # Read-only probe: the sentinel survives byte-for-byte.
    assert sentinel.read_text(encoding="utf-8") == "operator stop\n"


def test_gate_context_is_bounded_fail_closed_and_self_describing(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _read_adapter(fixture)

    ctx = build_gate_context(
        read_adapter=adapter,
        board=fixture.board,
        task_id="child-blocked",
        surface="beta",
        residual_risk=["provider flaps under load"],
    )

    assert ctx.task_id == "child-blocked"
    assert ctx.board == fixture.board
    assert ctx.evidence.task_status == "blocked"
    assert ctx.evidence.dispatch_state == "BLOCKED"
    # Blocked fixture task carries its block kind into surfaced risk.
    assert any(reason.startswith("dispatch:") for reason in ctx.residual_risk)
    assert "provider flaps under load" in ctx.residual_risk
    assert ctx.decision_options == ("YES", "NO")
    assert ctx.rollback.startswith(f"Board {fixture.board} task child-blocked")

    markdown = format_gate_markdown(ctx)
    assert "# Human Gate" in markdown
    assert "`YES`" in markdown and "`NO`" in markdown
    assert "Self-approval is rejected" in markdown
    assert ctx.provenance.provenance_header.endswith("/beta")
    assert ctx.provenance.baseline_mcp_sha == BASELINE_MCP_SHA

    prov = provenance_bundle("stable")
    assert prov.surface == "stable"
    assert len(prov.provenance_header.split("/")) == 3
    assert all(prov.provenance_header.split("/"))


def test_wave4_leaves_are_scoped_auditable_and_bounded(tmp_path: Path, monkeypatch):
    asyncio.run(_test_wave4_leaves_are_scoped_auditable_and_bounded(tmp_path, monkeypatch))


async def _test_wave4_leaves_are_scoped_auditable_and_bounded(tmp_path: Path, monkeypatch):
    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    # Route the read-only pause probe at an empty home so the host state
    # cannot influence the assertion.
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    reader = _token(auth, "gate-reader", ["hermes:read"])
    manager = _token(auth, "gate-manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            gate = _assert_success(
                await _rpc(
                    client,
                    reader,
                    "tools/call",
                    {
                        "name": "human-gate",
                        "arguments": {
                            "request": {"board": fixture.board, "task_id": "review-task"}
                        },
                    },
                    1,
                )
            )
            assert gate["task_id"] == "review-task"
            assert gate["board"] == fixture.board
            assert gate["decision_options"] == ["YES", "NO"]
            assert gate["provenance"]["baseline_mcp_sha"] == BASELINE_MCP_SHA
            assert gate["provenance"]["api_version"] == API_VERSION
            assert gate["evidence"]["task_title"] == "Review task"
            assert "# Human Gate" in gate["markdown"]

            # A read-only token cannot record decisions.
            denied = await _rpc(
                client,
                reader,
                "tools/call",
                {
                    "name": "human-gate-decide",
                    "arguments": {
                        "request": {"board": fixture.board, "task_id": "review-task", "decision": "YES"}
                    },
                },
                2,
            )
            _assert_error(denied, "SCOPE_REQUIRED")

            # Self-approval is structurally rejected before any write happens.
            self_approval = await _rpc(
                client,
                manager,
                "tools/call",
                {
                    "name": "human-gate-decide",
                    "arguments": {
                        "request": {
                            "board": fixture.board,
                            "task_id": "review-task",
                            "decision": "YES",
                            "requester": "gate-manager",
                        }
                    },
                },
                3,
            )
            _assert_error(self_approval, "CONFLICT")

            decided = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "human-gate-decide",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "task_id": "review-task",
                                "decision": "YES",
                                "reason": "evidence complete",
                            }
                        },
                    },
                    4,
                )
            )
            assert decided["recorded"] is True
            assert decided["decision"] == "YES"
            assert decided["comment_id"] > 0

            activity = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "get_activity",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "task_id": "review-task",
                                "max_items": 50,
                                "log_bytes": 0,
                            }
                        },
                    },
                    5,
                )
            )
            bodies = [comment["body"] for comment in activity["comments"]]
            assert any(body.startswith("HUMAN_GATE YES") for body in bodies)
            assert any("Reason: evidence complete" in body for body in bodies)

            status = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "control-status",
                        "arguments": {
                            "request": {"board": fixture.board, "include_dispatch_dry_run": False}
                        },
                    },
                    6,
                )
            )
            assert status["daemon"]["status"] == "available"
            assert status["daemon"]["bounded"] is True
            assert status["control_plane"]["api_version"] == API_VERSION
            assert status["pause"]["paused"] is False
            assert status["drain_preview"] == {
                "board": fixture.board,
                "cleaned_events": 0,
                "cleaned_logs": 0,
                "cleaned_temp": 0,
            }
            assert isinstance(status["stats"], dict)

            canary = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {
                        "name": "canary",
                        "arguments": {
                            "request": {
                                "board": fixture.board,
                                "build_commit": "b" * 40,
                                "surface": "beta",
                                "deployed_at": "2026-08-26T00:00:00Z",
                            }
                        },
                    },
                    7,
                )
            )
            assert canary["verified"] is True
            assert canary["manifest"]["api_version"] == API_VERSION
            assert canary["manifest"]["baseline_mcp_sha"] == BASELINE_MCP_SHA


def test_healthz_still_serves_after_wave4_registration(tmp_path: Path, monkeypatch):
    asyncio.run(_test_healthz_still_serves_after_wave4_registration(tmp_path, monkeypatch))


async def _test_healthz_still_serves_after_wave4_registration(tmp_path: Path, monkeypatch):
    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-API-Version"] == API_VERSION
    assert response.headers["X-Baseline-MCP"] == BASELINE_MCP_SHA[:12]
