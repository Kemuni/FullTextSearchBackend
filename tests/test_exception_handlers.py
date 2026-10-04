from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exception_handlers import error_response, register_exception_handlers
from app.schemas import PostPublic


async def test_error_response_has_only_the_public_error_contract() -> None:
    response = error_response("bad_request", "Invalid input", 400, {"X-Test": "1"})

    assert response.status_code == 400
    assert response.headers["X-Test"] == "1"
    assert response.body == (
        b'{"success":false,"data":null,"errors":{"code":"bad_request",'
        b'"message":"Invalid input"}}'
    )


async def test_exception_handlers_do_not_leak_internal_details() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("database password must not be exposed")

    @test_app.get("/needs-query")
    async def needs_query(value: int) -> dict[str, int]:
        return {"value": value}

    @test_app.get("/invalid", response_model=PostPublic)
    async def invalid_response() -> dict[str, int]:
        return {"id": 1}

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        validation = await client.get("/needs-query")
        internal_error = await client.get("/boom")
        response_validation = await client.get("/invalid")

    expected_internal = {
        "success": False,
        "data": None,
        "errors": {"code": "internal_error", "message": "Внутренняя ошибка сервера"},
    }
    assert validation.status_code == 422
    assert validation.json()["errors"]["code"] == "validation_error"
    assert internal_error.status_code == 500
    assert internal_error.json() == expected_internal
    assert "password" not in internal_error.text
    assert response_validation.status_code == 500
    assert response_validation.json() == {
        "success": False,
        "data": None,
        "errors": {
            "code": "internal_error",
            "message": "Не удалось сформировать ответ",
        },
    }
