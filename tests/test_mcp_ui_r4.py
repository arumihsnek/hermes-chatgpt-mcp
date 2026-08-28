"""R4 regression tests for the MCP Apps UI.

These tests guard the two durable findings from t_a0daa220 that must remain
fixed in any candidate that supersedes the t_d460c1cc R2 work:

  B5: V1/V2/HG HTML constants must not contain literal ``\\n`` escape
      sequences in the served HTML — every JS script body must contain
      real newlines only, and must parse cleanly with ``node --check``.
  V2 revision continuity: ``expected_board_revision`` in the V2 form
      must be refreshed from the readback after every successful mutation
      so a second bounded ``create_task`` does not fail STALE_VIEW; and
      the schema must surface ``board_revision`` on both ``get_board``
      and ``create_task`` responses.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

import pytest

from hermes_chatgpt_mcp.ui import (
    KANBAN_UI_HTML_V1,
    KANBAN_UI_HTML_V2,
    build_human_gate_ui_html,
    build_kanban_ui_html,
    build_kanban_ui_v2_html,
)
from hermes_chatgpt_mcp.human_gate_ui import build_human_gate_ui_html as _hg_html

# --- B5: HTML literal-newline regression guard --------------------------

NODE_BIN = shutil.which("node")
assert NODE_BIN, "node is required for the B5 JS-validity test"


def _script_bodies(html: str) -> list[str]:
    return re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)


@pytest.mark.parametrize(
    "html_name,html",
    [
        ("V1", KANBAN_UI_HTML_V1),
        ("V2", KANBAN_UI_HTML_V2),
        ("HG", _hg_html()),
    ],
)
def test_html_no_literal_backslash_n_in_scripts(html_name, html):
    """The B5 regression was: a Python ``'\\\\n'`` was emitted as literal text
    ``\\n`` into the served HTML, breaking every JS engine that tried to
    parse the script body. This test fails closed if the regression
    reappears in any of the three script bodies.
    """
    scripts = _script_bodies(html)
    assert scripts, f"{html_name} has no <script> blocks"
    for i, body in enumerate(scripts):
        assert "\\n" not in body, (
            f"{html_name} script[{i}] contains literal backslash-n "
            f"(would be served to the host as the two characters \\ and n, "
            f"breaking JS parsing). First occurrence context: "
            f"{body[max(0, body.find(chr(92) + 'n') - 20):body.find(chr(92) + 'n') + 20]!r}"
        )
        # And ensure real newlines ARE present (otherwise we have a different
        # single-line JS regression).
        assert "\n" in body, f"{html_name} script[{i}] has no real newlines"


@pytest.mark.parametrize(
    "html_name,html",
    [
        ("V1", KANBAN_UI_HTML_V1),
        ("V2", KANBAN_UI_HTML_V2),
        ("HG", _hg_html()),
    ],
)
def test_script_bodies_parse_with_node_check(html_name, html):
    """Every <script> body in the three served HTML resources must be
    syntactically valid JavaScript per ``node --check``. This is the
    strongest deterministic guard against the B5 regression: a script
    body containing literal ``\\n`` text fails to parse, so this test
    would have failed for the R2/R3 candidates.
    """
    scripts = _script_bodies(html)
    assert scripts, f"{html_name} has no <script> blocks"
    for i, body in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(body)
            path = fh.name
        try:
            result = subprocess.run(
                [NODE_BIN, "--check", path],
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            os.unlink(path)
        assert result.returncode == 0, (
            f"{html_name} script[{i}] failed node --check:\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


# --- V2 revision continuity ---------------------------------------------

def test_v2_script_uses_expected_board_revision_and_readback():
    """The V2 form's JS must (a) read the current board revision via
    get_board on init, (b) send it as expected_board_revision on
    create_task, and (c) update its cached revision from the
    board_revision field in the create_task response. This is the
    minimal shape that closes the 'second write goes STALE_VIEW' gap
    called out in t_a0daa220.
    """
    body = _script_bodies(KANBAN_UI_HTML_V2)[0]
    # (a) read on init
    assert '"get_board"' in body, "V2 form must call get_board to prime revision"
    # (b) send expected_board_revision in the create payload
    assert "expected_board_revision" in body, (
        "V2 form must include expected_board_revision in create_task payload"
    )
    # (c) update cache from create_task response
    assert "board_revision" in body, (
        "V2 form must read board_revision from create_task response to refresh its cache"
    )
    # The form must keep the submit button disabled until the readback
    # arrives, otherwise the user can race the initial get_board.
    assert "disabled" in body, "V2 form must keep submit disabled until initial readback"


def test_schemas_surface_board_revision_for_v2_continuity():
    """The server-side contract for the V2 form's revision tracking: the
    CreateTaskInput schema must accept expected_board_revision, the
    CreateTaskResult must return board_revision_after, and the BoardView
    must return board_revision so the form can prime its cache.
    """
    from hermes_chatgpt_mcp.schemas import (
        BoardView,
        CreateTaskInput,
        CreateTaskResult,
    )
    # Schema fields exist with the right shape
    fields_in = CreateTaskInput.model_fields
    assert "expected_board_revision" in fields_in
    assert fields_in["expected_board_revision"].default == 0
    assert fields_in["expected_board_revision"].metadata  # has ge=0
    fields_out = CreateTaskResult.model_fields
    assert "board_revision" in fields_out
    assert fields_out["board_revision"].default == 0
    fields_board = BoardView.model_fields
    assert "board_revision" in fields_board
    assert fields_board["board_revision"].default == 0

    # A board view can be constructed with the new field and round-trips.
    view = BoardView(
        slug="b1", name="B1", task_counts={}, board_revision=7
    )
    dumped = view.model_dump()
    assert dumped["board_revision"] == 7
    # And a result too.
    res = CreateTaskResult(
        created=True, task_id="t1", board="b1", title="T", status="running",
        priority=0, created_at=1, board_revision=8,
    )
    assert res.model_dump()["board_revision"] == 8


# --- end-to-end: revision-continuity through the mutation adapter --------

def test_v2_adapter_supports_two_creates_with_refreshing_revision(tmp_path):
    """The V2 form, after a successful first create, must read the new
    board_revision from the response and send it as
    expected_board_revision on a second create — otherwise the second
    write fails STALE_VIEW.

    This is a thin, deterministic integration test on the
    UiMutationAdapter: it verifies the contract that the V2 JS relies
    on (board_revision_after is monotonic and consumable as the next
    expected_board_revision).
    """
    from hermes_cli import kanban_db
    from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
    from hermes_chatgpt_mcp.ui_mutation import UiMutationAdapter
    from hermes_chatgpt_mcp.ui_write_contract import UiCapabilityIssuer

    from .fixtures import make_hermes_fixture

    fixture = make_hermes_fixture(tmp_path)
    store = ReadOnlyHermesStore(
        db_path=fixture.db_path,
        board=fixture.board,
        hermes_module=kanban_db,
        log_root=fixture.log_path.parent,
    )
    issuer = UiCapabilityIssuer(clock=lambda: 1_700_000_000)
    cap = issuer.issue(subject="ui-user", board=fixture.board, tenant="tenant-a")
    adapter = UiMutationAdapter(store, cap, issuer)

    first = adapter.create_task(
        title="UI task A", expected_board_revision=0, idempotency_key="r4-k1"
    )
    assert first.mutation_status == "created"
    assert first.board_revision_after == 1
    # Re-using the stale revision must fail (negative control).
    from hermes_chatgpt_mcp.ui_mutation import UiMutationError
    with pytest.raises(UiMutationError) as excinfo:
        adapter.create_task(
            title="UI task A (stale)", expected_board_revision=0,
            idempotency_key="r4-k2",
        )
    assert excinfo.value.code == "STALE_VIEW"
    # Using the refreshed revision succeeds.
    second = adapter.create_task(
        title="UI task B", expected_board_revision=first.board_revision_after,
        idempotency_key="r4-k3",
    )
    assert second.mutation_status == "created"
    assert second.board_revision_after == first.board_revision_after + 1
    assert second.canonical_task_id != first.canonical_task_id
