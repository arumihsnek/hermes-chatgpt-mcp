"""V4.1 probe-mode safety — V4.1-PROBE-SAFETY-R5.

Opt-in ``probe: true`` on authority-bearing tools fails closed with a
deterministic PROBE_MODE_REFUSAL before any side effect or after scope
enforcement (scope failures surface as SCOPE_REQUIRED, never as
PROBE_MODE_REFUSAL).  Read-only tools remain unaffected.  Human-gate
self-approval is structurally rejected independent of probe mode.
"""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from contextlib import closing
from dataclasses import replace

import httpx
import pytest

from hermes_chatgpt_mcp.probe_mode import enforce_probe_safe, is_probe_request, probe_refusal_payload
from hermes_chatgpt_mcp.schemas import (
    AddCommentInput,
    AssignTaskInput,
    AttachInput,
    ClaimInput,
    CreateBoardInput,
    CreateTaskInput,
    DispatchInput,
    HumanGateDecisionInput,
    ListTasksInput,
    ProbeModeRefusal,
    RenameBoardInput,
    SwarmInput,
    TaskInput,
)
from hermes_chatgpt_mcp.server import create_app
from hermes_cli import kanban_db

from .test_auth import _settings
from .test_beta_integration import _assert_success, _beta_fixture, _rpc, _token


# ── schema contracts ───────────────────────────────────────────


def test_probe_default_is_false_and_reads_have_no_probe_field():
    assert CreateTaskInput(board="b", title="t", idempotency_key="probe-x").probe is False
    assert CreateBoardInput(slug="beta-board-x", name="X").probe is False
    assert AddCommentInput(board="b", task_id="t", body="c").probe is False
    assert AssignTaskInput(board="b", task_id="t", assignee="w").probe is False
    assert SwarmInput(board="b", goal="g", workers=["a"], verifier="a", synthesizer="a").probe is False
    assert DispatchInput(board="b").probe is False
    assert ClaimInput(board="b", task_id="t").probe is False
    assert RenameBoardInput(slug="b").probe is False
    assert HumanGateDecisionInput(board="b", task_id="t", decision="YES").probe is False
    # Reads never carry a probe channel; their schemas have no probe field.
    assert not hasattr(ListTasksInput(board="b"), "probe")
    assert not hasattr(TaskInput(board="b", task_id="t"), "probe")


def test_probe_roundtrip_is_preserved():
    assert CreateTaskInput(board="b", title="t", idempotency_key="probe-y", probe=True).probe is True
    assert RenameBoardInput(slug="b", probe=True).probe is True


# ── probe_mode helpers ───────────────────────────────────────


def test_is_probe_request_is_strictly_opt_in():
    class Probeful:
        probe = True

    class ProbeOff:
        probe = False

    class ProbeAbsent:
        pass

    assert is_probe_request(Probeful()) is True
    assert is_probe_request(ProbeOff()) is False
    assert is_probe_request(ProbeAbsent()) is False
    assert is_probe_request(None) is False


def test_enforce_probe_safe_no_side_effect_for_normal_calls():
    enforce_probe_safe(CreateTaskInput(board="b", title="t", idempotency_key="probe-x"), "create_task")
    enforce_probe_safe(AddCommentInput(board="b", task_id="t", body="c"), "add_comment")


def test_enforce_probe_safe_raises_deterministic_tool_error():
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError) as excinfo:
        enforce_probe_safe(CreateTaskInput(board="b", title="t", idempotency_key="probe-y", probe=True), "create_task")
    rendered = str(excinfo.value)
    assert '"code":"PROBE_MODE_REFUSAL"' in rendered
    assert '"tool_name":"create_task"' in rendered
    assert '"refused":true' in rendered
    assert '"executed":false' in rendered
    assert "Traceback" not in rendered


def test_probe_refusal_payload_shape():
    payload = probe_refusal_payload("add_comment")
    assert ProbeModeRefusal(**payload).code == "PROBE_MODE_REFUSAL"
    assert payload["tool_name"] == "add_comment"
    assert payload["refused"] is True and payload["executed"] is False
    assert payload["attempted"] is True


def test_probe_refusal_is_typed_shapeless_failure():
    # The refusal body is the typed ProbeModeRefusal model, never a stack trace
    # or the request payload.  Failure callers must not be able to fingerprint
    # internal paths from the message.
    from mcp.server.fastmcp.exceptions import ToolError
    import json

    with pytest.raises(ToolError) as excinfo:
        enforce_probe_safe(SwarmInput(board="b", goal="g", workers=["a"], verifier="a", synthesizer="a", probe=True), "swarm")
    body = json.loads(str(excinfo.value))
    assert set(body.keys()) == {"code", "message", "tool_name", "refused", "attempted", "executed"}
    assert body["code"] == "PROBE_MODE_REFUSAL"
    # Message is fixed, never echoed from the goal.
    assert "g" not in body["message"]


# ── beta surface integration ──────────────────────────────────


def _assert_probe_refusal(result: dict) -> None:
    payload = result["result"]
    assert payload["isError"] is True
    rendered = " ".join(str(item.get("text", "")) for item in payload.get("content", []))
    assert '"code":"PROBE_MODE_REFUSAL"' in rendered
    assert "Traceback" not in rendered
    assert "stack" not in rendered.lower()


def _board_state_fingerprint(db_path: str) -> str:
    digest = hashlib.sha256()
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
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


def _assert_scope_required(result: dict) -> None:
    payload = result["result"]
    assert payload["isError"] is True
    rendered = " ".join(str(item.get("text", "")) for item in payload.get("content", []))
    assert '"code":"SCOPE_REQUIRED"' in rendered


def test_beta_probe_mode_refuses_authority_writes_and_leaves_reads(tmp_path, monkeypatch):
    asyncio.run(_test_beta_probe_mode_refuses_authority_writes_and_leaves_reads(tmp_path, monkeypatch))


async def _test_beta_probe_mode_refuses_authority_writes_and_leaves_reads(tmp_path, monkeypatch):
    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    board = fixture.board
    fingerprint_before = _board_state_fingerprint(fixture.db_path)

    admin = _token(auth, "probe-admin", ["hermes:read", "hermes:manage", "hermes:admin", "hermes:board:create"], board=board)
    manager = _token(auth, "probe-manager", ["hermes:read", "hermes:manage"], board=board)
    creator = _token(auth, "probe-creator", ["hermes:read", "hermes:create"], board=board)
    reader = _token(auth, "probe-reader", ["hermes:read"], board=None)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            for request_id, (name, arguments) in enumerate(
                [
                    ("list_boards", {}),
                    ("get_board", {"request": {"board": board}}),
                    ("list_tasks", {"request": {"board": board, "limit": 5}}),
                    ("get_task", {"request": {"board": board, "task_id": "review-task"}}),
                    ("get_task_graph", {"request": {"board": board, "task_id": "review-task", "depth": 1, "max_nodes": 5}}),
                    ("get_dispatch", {"request": {"board": board, "task_id": "child-blocked"}}),
                    ("get_activity", {"request": {"board": board, "task_id": "review-task", "max_items": 5, "log_bytes": 100}}),
                    ("human-gate", {"request": {"board": board, "task_id": "review-task"}}),
                ],
                start=1,
            ):
                _assert_success(await _rpc(client, reader, "tools/call", {"name": name, "arguments": arguments}, request_id))

            write_matrix: list[tuple[str, dict, str]] = [
                ("create_task", {"request": {"board": board, "title": "probe-create", "idempotency_key": "probe-create-1", "probe": True}}, creator),
                ("create_board", {"request": {"slug": "probe-new-board", "name": "Probe Board", "probe": True}}, admin),
                ("add_comment", {"request": {"board": board, "task_id": "review-task", "body": "probe comment", "probe": True}}, manager),
                ("assign_task", {"request": {"board": board, "task_id": "review-task", "assignee": "worker-2", "probe": True}}, manager),
                ("link_tasks", {"request": {"board": board, "parent_id": "child-ready", "child_id": "review-task", "probe": True}}, manager),
                ("unlink_tasks", {"request": {"board": board, "parent_id": "child-ready", "child_id": "review-task", "probe": True}}, manager),
                ("set_model", {"request": {"board": board, "task_id": "review-task", "model": "probe-model", "probe": True}}, manager),
                ("reclaim_task", {"request": {"board": board, "task_id": "child-running", "probe": True}}, manager),
                ("swarm", {"request": {"board": board, "goal": "probe goal", "workers": ["worker-1"], "verifier": "worker-2", "synthesizer": "worker-3", "probe": True}}, admin),
                ("attach", {"request": {"board": board, "task_id": "review-task", "local_path": "/tmp/probe.txt", "probe": True}}, admin),
                ("boards-rename", {"request": {"slug": board, "name": "Probe Rename", "probe": True}}, admin),
                ("dispatch", {"request": {"board": board, "probe": True}}, admin),
                ("claim", {"request": {"board": board, "task_id": "child-ready", "probe": True}}, admin),
                ("human-gate-decide", {"request": {"board": board, "task_id": "review-task", "decision": "YES", "probe": True}}, manager),
            ]

            for request_id, (name, arguments, token) in enumerate(write_matrix, start=50):
                _assert_probe_refusal(await _rpc(client, token, "tools/call", {"name": name, "arguments": arguments}, request_id))

            _assert_scope_required(
                await _rpc(
                    client,
                    reader,
                    "tools/call",
                    {"name": "add_comment", "arguments": {"request": {"board": board, "task_id": "review-task", "body": "nope", "probe": True}}},
                    200,
                )
            )

            self_approval = await _rpc(
                client,
                manager,
                "tools/call",
                {"name": "human-gate-decide", "arguments": {"request": {"board": board, "task_id": "review-task", "decision": "YES", "requester": "probe-manager"}}},
                201,
            )
            from .test_beta_integration import _assert_error  # type: ignore

            _assert_error(self_approval, "CONFLICT")

            assert _board_state_fingerprint(fixture.db_path) == fingerprint_before
            _assert_success(await _rpc(client, admin, "tools/call", {"name": "get_board", "arguments": {"request": {"board": board}}}, 300))


def test_probe_false_still_executes_normal_path(tmp_path, monkeypatch):
    asyncio.run(_test_probe_false_still_executes_normal_path(tmp_path, monkeypatch))


async def _test_probe_false_still_executes_normal_path(tmp_path, monkeypatch):
    fixture, _board_b, settings, auth, app = _beta_fixture(tmp_path, monkeypatch)
    board = fixture.board
    manager = _token(auth, "probe-manager-real", ["hermes:read", "hermes:manage"], board=board)
    creator = _token(auth, "probe-creator-real", ["hermes:read", "hermes:create"], board=board)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url=settings.public_base_url) as client:
            created = _assert_success(
                await _rpc(
                    client,
                    creator,
                    "tools/call",
                    {"name": "create_task", "arguments": {"request": {"board": board, "title": "real-create-probe-false", "idempotency_key": "probe-real-1", "probe": False}}},
                    1,
                )
            )
            assert created["task_id"]
            commented = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {"name": "add_comment", "arguments": {"request": {"board": board, "task_id": "review-task", "body": "real comment", "probe": False}}},
                    2,
                )
            )
            assert commented["task_id"] == "review-task"
            assigned = _assert_success(
                await _rpc(
                    client,
                    manager,
                    "tools/call",
                    {"name": "assign_task", "arguments": {"request": {"board": board, "task_id": created["task_id"], "assignee": "worker-2"}}},
                    3,
                )
            )
            assert assigned["assignee"] == "worker-2"
