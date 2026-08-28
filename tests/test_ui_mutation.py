from hermes_cli import kanban_db

from hermes_chatgpt_mcp.hermes import ReadOnlyHermesStore
from hermes_chatgpt_mcp.ui_mutation import UiMutationAdapter, UiMutationError
from hermes_chatgpt_mcp.ui_write_contract import UiCapabilityIssuer

from .fixtures import make_hermes_fixture


def _adapter(tmp_path):
    fixture = make_hermes_fixture(tmp_path)
    store = ReadOnlyHermesStore(db_path=fixture.db_path, board=fixture.board,
                                hermes_module=kanban_db, log_root=fixture.log_path.parent)
    cap = UiCapabilityIssuer(clock=lambda: 1_700_000_000).issue(
        subject="ui-user", board=fixture.board, tenant="tenant-a")
    return fixture, UiMutationAdapter(store, cap, UiCapabilityIssuer(clock=lambda: 1_700_000_000))


def test_ui_create_replay_and_conflict(tmp_path):
    _, adapter = _adapter(tmp_path)
    first = adapter.create_task(title="UI task", expected_board_revision=0, idempotency_key="k1")
    assert first.mutation_status == "created"
    replay = adapter.create_task(title="UI task", expected_board_revision=0, idempotency_key="k1")
    assert replay.mutation_status == "idempotent_replay"
    assert replay.canonical_task_id == first.canonical_task_id
    try:
        adapter.create_task(title="other", expected_board_revision=0, idempotency_key="k1")
    except UiMutationError as exc:
        assert exc.code == "IDEMPOTENCY_CONFLICT"
    else:
        raise AssertionError("conflicting replay was accepted")


def test_ui_stale_and_forbidden_fields(tmp_path):
    _, adapter = _adapter(tmp_path)
    try:
        adapter.create_task(title="stale", expected_board_revision=4, idempotency_key="k2")
    except UiMutationError as exc:
        assert exc.code == "STALE_VIEW"
    else:
        raise AssertionError("stale write was accepted")
    try:
        adapter.create_task(title="bad", expected_board_revision=0, idempotency_key="k3", assignee="worker")
    except UiMutationError as exc:
        assert exc.code == "UI_FIELD_FORBIDDEN"
    else:
        raise AssertionError("forbidden field was accepted")
