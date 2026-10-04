from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import OutboxAction, OutboxStatus, Post
from app.schemas import ErrorDetail, ErrorResponse, PostIn, PostPublic, SuccessResponse


def test_post_in_has_independent_default_rubrics() -> None:
    first = PostIn(text="first")
    second = PostIn(text="second")

    first.rubrics.append("news")

    assert second.rubrics == []


def test_post_public_reads_orm_model() -> None:
    now = datetime.now(UTC)
    post = Post(
        id=7,
        text="Привет 👋 Hello",
        rubrics=["VK-7"],
        created_date=now,
        updated_at=now,
    )

    assert PostPublic.model_validate(post).model_dump() == {
        "text": "Привет 👋 Hello",
        "rubrics": ["VK-7"],
        "id": 7,
        "created_date": now,
        "updated_at": now,
    }


def test_response_schemas_enforce_success_and_error_shapes() -> None:
    assert SuccessResponse(data="ok").model_dump() == {
        "success": True,
        "data": "ok",
        "errors": None,
    }
    assert (
        ErrorResponse(errors=ErrorDetail(code="bad", message="Bad request")).data
        is None
    )

    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(
            {"errors": {"code": "bad", "message": "Bad"}, "data": "leak"}
        )


def test_outbox_enums_have_database_values() -> None:
    assert {member.value for member in OutboxStatus} == {
        "pending",
        "in_progress",
        "completed",
    }
    assert {member.value for member in OutboxAction} == {"create", "update", "delete"}
