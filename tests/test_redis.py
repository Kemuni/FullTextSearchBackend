import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import redis as redis_core


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:  # noqa: ARG002
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:  # noqa: ARG002
        return None

    async def ttl(self, key: str) -> int:  # noqa: ARG002
        return 42


async def test_cache_helpers_and_rate_limit(monkeypatch) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr(redis_core, "redis_client", fake_redis)

    await redis_core.set_cached_value("post:1", '{"id": 1}', 60)
    assert await redis_core.get_cached_value("post:1") == '{"id": 1}'
    await redis_core.delete_cached_value("post:1")
    assert await redis_core.get_cached_value("post:1") is None

    request = Request({"type": "http", "client": ("127.0.0.1", 12345)})
    limiter = redis_core.rate_limit("test", limit=2, window_seconds=60)
    await limiter(request)
    await limiter(request)
    with pytest.raises(HTTPException) as exception:
        await limiter(request)

    assert exception.value.status_code == 429
    assert exception.value.headers == {"Retry-After": "42"}
