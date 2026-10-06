import logging
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request
from redis import RedisError
from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: Redis = from_url(settings.REDIS_URL, decode_responses=True)
RedisUnavailableErrors = (RedisError, RuntimeError)


async def get_cached_value(key: str) -> str | bytes | None:
    try:
        return await redis_client.get(key)
    except RedisUnavailableErrors:
        logger.warning("Redis is unavailable; skipping cache read", exc_info=True)
        return None


async def set_cached_value(key: str, value: str, ttl: int) -> None:
    try:
        await redis_client.set(key, value, ex=ttl)
    except RedisUnavailableErrors:
        logger.warning("Redis is unavailable; skipping cache write", exc_info=True)


async def delete_cached_value(key: str) -> None:
    try:
        await redis_client.delete(key)
    except RedisUnavailableErrors:
        logger.warning(
            "Redis is unavailable; skipping cache invalidation", exc_info=True
        )


def rate_limit(
    scope: str, limit: int, window_seconds: int
) -> Callable[[Request], Awaitable[None]]:
    """Создает rate-limiter нас основе IP"""

    async def check_rate_limit(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate-limit:{scope}:{client_ip}"
        try:
            request_count = await redis_client.incr(key)  # type: ignore
            if request_count == 1:
                await redis_client.expire(key, window_seconds)
            if request_count > limit:
                retry_after = max(await redis_client.ttl(key), 1)
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
        except RedisUnavailableErrors:
            logger.warning("Redis is unavailable; skipping rate limit", exc_info=True)

    return check_rate_limit


read_rate_limit = rate_limit(
    "read", settings.READ_RATE_LIMIT, settings.RATE_LIMIT_WINDOW_SECONDS
)
write_rate_limit = rate_limit(
    "write", settings.WRITE_RATE_LIMIT, settings.RATE_LIMIT_WINDOW_SECONDS
)
