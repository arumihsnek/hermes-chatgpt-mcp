from __future__ import annotations

import pytest
from pydantic import ValidationError

from hermes_chatgpt_mcp.schemas import (
    AddCommentInput,
    AddCommentResult,
    AssignTaskInput,
    AssignTaskResult,
    BetaBoardCapabilities,
    BetaBoardListView,
    BetaBoardSummary,
    BoardCapabilities,
    BoardListView,
    CreateBoardInput,
    CreateBoardResult,
    GlobalCapabilities,
)


def test_beta_capabilities_and_list_are_separate_from_stable_wire_shape():
    stable = BoardListView(
        items=[], default_board="main"
    )
    beta = BetaBoardListView(
        items=[],
        default_board="main",
        global_capabilities=GlobalCapabilities(create_board=True),
    )

    assert stable.model_dump() == {"items": [], "default_board": "main"}
    assert beta.model_dump() == {
        "items": [],
        "default_board": "main",
        "global_capabilities": {"create_board": True},
    }
    assert set(BetaBoardCapabilities.model_fields) == {"read", "create", "manage"}
    assert set(BoardCapabilities.model_fields) == {"read", "create"}
    assert set(BetaBoardSummary.model_fields) >= {"capabilities"}


def test_create_board_input_accepts_bounded_safe_metadata():
    request = CreateBoardInput(
        slug="design-board",
        name="Design Board",
        description="A board for design work.",
        icon="kanban",
        color="#2563eb",
    )

    assert request.slug == "design-board"
    assert request.model_dump(exclude_none=True) == {
        "slug": "design-board",
        "name": "Design Board",
        "description": "A board for design work.",
        "icon": "kanban",
        "color": "#2563eb",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"slug": "../escape"},
        {"slug": "bad slug"},
        {"slug": "/tmp/board"},
        {"slug": "ok", "unknown": True},
        {"slug": "ok", "icon": "/tmp/icon.svg"},
        {"slug": "ok", "color": "../red"},
        {"slug": "ok", "name": "n" * 513},
        {"slug": "ok", "description": "d" * 2_001},
    ],
)
def test_create_board_input_rejects_invalid_or_path_like_fields(payload):
    with pytest.raises(ValidationError):
        CreateBoardInput.model_validate(payload)


def test_comment_and_assignment_inputs_are_strict_and_valid():
    comment = AddCommentInput(board="main", task_id="task_123", body="Looks good")
    assignment = AssignTaskInput(board="main", task_id="task_123", assignee="planner")

    assert comment.model_dump() == {
        "board": "main",
        "task_id": "task_123",
        "body": "Looks good",
    }
    assert assignment.model_dump() == {
        "board": "main",
        "task_id": "task_123",
        "assignee": "planner",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"board": "bad slug", "task_id": "task_123", "body": "x"},
        {"board": "main", "task_id": "bad id!", "body": "x"},
        {"board": "main", "task_id": "task_123", "body": ""},
        {"board": "main", "task_id": "task_123", "body": "x" * 16_001},
        {"board": "main", "task_id": "task_123", "body": "x", "extra": 1},
    ],
)
def test_add_comment_input_rejects_invalid_payloads(payload):
    with pytest.raises(ValidationError):
        AddCommentInput.model_validate(payload)


def test_assign_task_input_rejects_invalid_task_or_assignee():
    with pytest.raises(ValidationError):
        AssignTaskInput(board="main", task_id="", assignee="planner")
    with pytest.raises(ValidationError):
        AssignTaskInput(board="main", task_id="task_123", assignee="")
    with pytest.raises(ValidationError):
        AssignTaskInput(board="main", task_id="task_123", assignee="bad name")


def test_beta_results_expose_safe_fields_only():
    board = CreateBoardResult(
        slug="main",
        name="Main",
        description="",
        created=True,
        is_default=False,
    )
    comment = AddCommentResult(
        board="main", task_id="task_123", comment_id=4, author="chatgpt_mcp", created_at=10
    )
    assignment = AssignTaskResult(
        board="main", task_id="task_123", assignee="planner", status="ready"
    )

    assert "path" not in board.model_dump()
    assert comment.comment_id == 4
    assert assignment.status == "ready"
