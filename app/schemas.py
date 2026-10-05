import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse[T](BaseModel):  # noqa: UP046
    """Базовый единый формат ответа нашего API"""

    success: bool
    data: T | None = None
    errors: ErrorDetail | None = None


class SuccessResponse[T](APIResponse[T]):  # noqa
    success: Literal[True] = True
    errors: None = None


class ErrorResponse(APIResponse[None]):  # noqa
    success: Literal[False] = False
    data: None = None
    errors: ErrorDetail


class PostIn(BaseModel):
    text: str
    rubrics: list[str] = Field(default_factory=list)


class InitPostIn(PostIn):
    """Схема поста для init данных"""

    created_date: datetime.datetime | None = None


class PostPublic(PostIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_date: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None


class OutboxPostPayload(BaseModel):
    """Схема для payload Outbox-события"""

    id: int
    text: str
    rubrics: list[str] = Field(default_factory=list)
    created_date: datetime.datetime
    updated_at: datetime.datetime
