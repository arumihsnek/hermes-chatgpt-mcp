from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import httpx
import pytest

from hermes_chatgpt_mcp.adapter import HermesReadOnlyAdapter
from hermes_chatgpt_mcp.boards import BoardHandle
from hermes_chatgpt_mcp.command import HermesCardManagementAdapter
from hermes_chatgpt_mcp.control_plane import (
    DELIVERY_MODES,
    bounded_notify_list,
    bounded_notify_subscribe,
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
from hermes_chatgpt_mcp.provenance import API_VERSION, BASELINE_BRANCH, BASELINE_MCP_SHA

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


def _management_adapter_for(fixture) -> HermesCardManagementAdapter:
    handle = BoardHandle(
        slug=fixture.board,
        name="Fixture Board",
        description="Representative board",
        project_id=None,
        created_at=None,
        is_default=True,
        db_path=fixture.db_path,
    )
    return HermesCardManagementAdapter(handle, kanban_db)


def _notify_rows(fixture) -> list[sqlite3.Row]:
    with closing(sqlite3.connect(fixture.db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM kanban_notify_subs WHERE task_id = ? ORDER BY platform, chat_id",
            ("review-task",),
        ).fetchall()


def _board_state_fingerprint(fixture) -> str:
    """Fingerprint only the canonical board tables, ignoring volatile SQLite
    sidecars (WAL/checkpoint bytes) that reads may legitimately touch."""
    digest = hashlib.sha256()
    with closing(sqlite3.connect(f"file:{fixture.db_path}?mode=ro", uri=True)) as conn:
        for table in (
            "tasks",
            "task_links",
            "task_comments",
            "task_events",
            "task_runs",
            "task_attachments",
            "kanban_notify_subs",
        ):
            digest.update(table.encode("utf-8"))
            for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1"):
                digest.update(repr(row).encode("utf-8"))
    return digest.hexdigest()


def test_duplicate_notification_subscribe_is_durable_and_idempotent(tmp_path, monkeypatch):
    fixture = make_hermes_fixture(tmp_path)
    adapter = _management_adapter_for(fixture)

    first = adapter.notify_subscribe(
        "review-task", "", platform="telegram", chat_id="ops-room", delivery="wake"
    )
    second = adapter.notify_subscribe(
        "review-task", "", platform="telegram", chat_id="ops-room", delivery="wake"
    )

    assert first["subscribed"] is True and second["subscribed"] is True
    rows = _notify_rows(fixture)
    assert len(rows) == 1
    assert rows[0]["delivery_mode"] == "wake"
    # The durable row snaps to the task's current event cursor so a fresh
    # subscriber never replays historical terminal events (boundedness).
    assert int(rows[0]["last_event_id"]) > 0

    # Re-subscribing through the bounded domain helper keeps exactly one row.
    bounded = bounded_notify_subscribe(
        manage_adapter=adapter,
        task_id="review-task",
        platform="telegram",
        chat_id="ops-room",
        delivery="wake",
    )
    assert bounded["subscribed"] is True
    assert len(_notify_rows(fixture)) == 1


def test_notify_list_page_bound_is_enforced_at_the_domain_boundary():
    class Adapter:
        def __init__(self):
            self.calls: list[int] = []

        def notify_list(self, limit, task_id=None):
            self.calls.append(limit)
            return [{"task_id": "review-task"}]

    adapter = Adapter()
    for bad_limit in (0, -1, 1001, 10_000):
        with pytest.raises(ValueError, match="limit"):
            bounded_notify_list(manage_adapter=adapter, limit=bad_limit)
    assert adapter.calls == []


def test_canary_verifier_fails_closed_on_tampered_baseline_contract():
    bundle = build_canary_bundle(
        build_commit="c" * 40, surface="beta", deployed_at="2026-08-26T00:00:00Z"
    )
    assert bundle.verified is True

    # An arbitrary baseline branch/sha must never pass as provenance: only the
    # frozen v4 contract values are acceptable in a detached canary manifest.
    for field, value in (("baseline_branch", "attacker/main"), ("baseline_mcp_sha", "f" * 40)):
        tampered = dict(bundle.manifest, **{field: value})
        rejected = verify_canary_manifest(tampered)
        assert rejected.verified is False
        assert rejected.manifest == {}
        assert rejected.errors

    # The frozen contract itself still verifies.
    assert verify_canary_manifest(dict(bundle.manifest)).verified is True
    assert verify_canary_manifest(dict(bundle.manifest)).manifest["baseline_branch"] == BASELINE_BRANCH


def _gate_decision_rpc(client, token, board, *, decision, requester=None, request_id=10):
    body = {
        "name": "human-gate-decide",
        "arguments": {
            "request": {
                "board": board,
                "task_id": "review-task",
                "decision": decision,
                "requester": requester,
                "reason": "stale-candidate policy probe",
            }
        },
    }
    return _rpc(client, token, "tools/call", body, request_id)


def test_stale_candidate_gate_decision_is_rejected_and_audited(tmp_path: Path, monkeypatch):
    asyncio.run(_test_stale_candidate_gate_decision_is_rejected_and_audited(tmp_path, monkeypatch))


async def _test_stale_candidate_gate_decision_is_rejected_and_audited(tmp_path: Path, monkeypatch):
    """A decision naming a requester that no longer matches an active candidate
    (superseded worker session) must fail closed instead of recording YES."""
    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    manager = _token(auth, "gate-manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            stale = await _gate_decision_rpc(
                client,
                manager,
                fixture.board,
                decision="YES",
                requester="worker-superseded-session-0001",
            )
            _assert_error(stale, "CONFLICT")

            # Nothing was recorded: no gate comment exists for the stale actor.
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
                    11,
                )
            )
            assert not any("HUMAN_GATE" in c["body"] for c in activity["comments"])


def test_gate_decisions_are_auditable_provenance_bound_and_append_only(tmp_path: Path, monkeypatch):
    asyncio.run(_test_gate_decisions_are_auditable_provenance_bound_and_append_only(tmp_path, monkeypatch))


async def _test_gate_decisions_are_auditable_provenance_bound_and_append_only(tmp_path: Path, monkeypatch):
    """Every recorded YES/NO lands as an immutable canonical comment authored by
    the MCP provenance identity; replaying the same decision appends another
    auditable event rather than mutating state."""
    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    manager = _token(auth, "gate-manager", ["hermes:read", "hermes:manage"], board=fixture.board)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            first = _assert_success(
                await _gate_decision_rpc(client, manager, fixture.board, decision="YES")
            )
            replay = _assert_success(
                await _gate_decision_rpc(
                    client, manager, fixture.board, decision="YES", request_id=12
                )
            )
            assert first["recorded"] is True and replay["recorded"] is True
            assert replay["comment_id"] != first["comment_id"]

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
                    13,
                )
            )
            decisions = [c for c in activity["comments"] if c["body"].startswith("HUMAN_GATE")]
            assert len(decisions) == 2
            assert all(c["author"] == "chatgpt_mcp" for c in decisions)
            assert all("Requester:" not in c["body"] for c in decisions)

            # The audit trail lives in canonical storage, not just the view.
            with closing(sqlite3.connect(fixture.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                comments = kanban_db.list_comments(conn, "review-task")
            gate_comments = [c for c in comments if c.body.startswith("HUMAN_GATE")]
            assert len(gate_comments) == 2
            assert all(c.author == "chatgpt_mcp" for c in gate_comments)


def test_control_status_snapshot_is_bounded_read_only_and_partial_failure_safe(
    tmp_path: Path, monkeypatch
):
    asyncio.run(_test_control_status_snapshot_is_bounded_read_only_and_partial_failure_safe(tmp_path, monkeypatch))


async def _test_control_status_snapshot_is_bounded_read_only_and_partial_failure_safe(
    tmp_path: Path, monkeypatch
):
    from hermes_chatgpt_mcp.control_plane import status_snapshot

    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    reader = _token(auth, "status-reader", ["hermes:read"])
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            before = _board_state_fingerprint(fixture)

            status = _assert_success(
                await _rpc(
                    client,
                    reader,
                    "tools/call",
                    {
                        "name": "control-status",
                        "arguments": {"request": {"board": fixture.board, "include_dispatch_dry_run": True}},
                    },
                    20,
                )
            )
            # Read-only: a full status snapshot mutates nothing on disk.
            assert status["drain_preview"]["cleaned_events"] == 0
            # The dry-run is a bounded preview: flagged as such and capped by
            # the canonical max_spawn bound, never a live spawn.
            assert status["dispatch_dry_run"]["dry_run"] is True
            assert len(status["dispatch_dry_run"]["spawned"]) <= 10
            assert _board_state_fingerprint(fixture) == before

            # Boundedness: daemon control exposes status/snapshot only — never a loop.
            daemon = await _rpc(
                client,
                reader,
                "tools/call",
                {"name": "control-status", "arguments": {"request": {"board": fixture.board}}},
                21,
            )
            assert daemon["result"]["isError"] is not True

            # Partial failure/retry: a backend error surfaces as a mapped tool
            # error, then the same read succeeds on retry without stale state.
            broken_resolver_board = fixture.board + "-missing"
            failed = await _rpc(
                client,
                reader,
                "tools/call",
                {
                    "name": "control-status",
                    "arguments": {
                        "request": {"board": broken_resolver_board, "include_dispatch_dry_run": False}
                    },
                },
                22,
            )
            assert failed["result"]["isError"] is True
            retried = _assert_success(
                await _rpc(
                    client,
                    reader,
                    "tools/call",
                    {
                        "name": "control-status",
                        "arguments": {
                            "request": {"board": fixture.board, "include_dispatch_dry_run": False}
                        },
                    },
                    23,
                )
            )
            assert retried["daemon"]["status"] == "available"
            assert retried["notify_count"] == 0
            assert retried["control_plane"]["mode"] == "bounded-snapshot"

    # Domain-level: a failing notify source degrades to notify_count=None while
    # the rest of the snapshot remains usable.
    class FlakyManage:
        def daemon(self, action="status"):
            return {"action": action, "bounded": True}

        def stats(self):
            return {}

        def dispatch(self, dry_run=True):
            raise RuntimeError("dispatch unavailable")

        def notify_list(self, limit=100, task_id=None):
            raise RuntimeError("notifier down")

        def gc(self, dry_run=True):
            return {"board": fixture.board, "cleaned_events": 0, "cleaned_logs": 0, "cleaned_temp": 0}

    snap = status_snapshot(read_adapter=None, manage_adapter=FlakyManage(), board=fixture.board)
    assert snap.notify_count is None
    assert "error" in (snap.dispatch_dry_run or {})
    assert snap.control_plane["api_version"] == API_VERSION
