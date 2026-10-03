import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def error_response(
    code: str,
    message: str,
    status_code: int,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Создает API ответ с ошибкой"""
    payload = ErrorResponse(errors=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрируем обработчики ошибок FastAPI приложения"""

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ()))
            message = str(error.get("msg", "Некорректное значение"))
            messages.append(f"{location}: {message}" if location else message)
        return error_response(
            "validation_error",
            "; ".join(messages) or "Некорректные входные данные",
            422,
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_exception_handler(
        _: Request, exc: ResponseValidationError
    ) -> JSONResponse:
        logger.exception("Response validation failed", exc_info=exc)
        return error_response("internal_error", "Не удалось сформировать ответ", 500)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Ошибка запроса"
        return error_response(
            f"http_{exc.status_code}", message, exc.status_code, headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=exc)
        return error_response("internal_error", "Внутренняя ошибка сервера", 500)
