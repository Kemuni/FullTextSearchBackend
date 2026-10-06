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
    updated_at: datetime.datetime | None = None


class PostPublic(PostIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_date: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None


class PaginatedResponse[T](BaseModel):
    page: int
    page_size: int
    total_pages: int
    data: list[T]


class SearchResponse[T](BaseModel):
    """Страница результатов, полученная с помощью курсора Elasticsearch."""

    old_cursor: str | None = None
    next_cursor: str | None = None
    page_size: int
    total: int
    data: list[T]


class OutboxPostPayload(BaseModel):
    """Схема для payload Outbox-события"""

    id: int
    text: str
    rubrics: list[str] = Field(default_factory=list)
    created_date: datetime.datetime
    updated_at: datetime.datetime


class PostSearchQuery(BaseModel):
    query: str = Field(default="", max_length=500, description="Текстовый запрос")
    page_size: int = Field(
        default=50, ge=1, le=100, description="Количество элементов на странице"
    )
    cursor: str | None = Field(default=None, description="Курсор для пагинации")
    rubrics: list[str] | None = Field(default=None, description="Список рубрик")
    created_from: datetime.datetime | None = Field(
        default=None, description="Дата создания с"
    )
    created_to: datetime.datetime | None = Field(
        default=None, description="Дата создания по"
    )
    sort_by: Literal["relevance", "created_date"] = Field(
        default="relevance", description="Поле для сортировки"
    )
    sort_order: Literal["asc", "desc"] = Field(
        default="desc", description="Порядок сортировки"
    )
