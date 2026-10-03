from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

from app.schemas import ErrorResponse

DEFAULT_ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Ресурс не найден"},
    422: {"model": ErrorResponse, "description": "Ошибка валидации запроса"},
    500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
}


class APIResponseRouter(APIRouter):
    """Описывает общую структуру ошибок для всех маршрутов API, не связанных со health-check."""

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        responses: dict[int | str, dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        if path.rstrip("/") != "/health-check":
            responses = {**DEFAULT_ERROR_RESPONSES, **(responses or {})}
        super().add_api_route(path, endpoint, responses=responses, **kwargs)
