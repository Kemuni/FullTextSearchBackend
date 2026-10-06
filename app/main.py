import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.elasticsearch import es_client
from app.core.exception_handlers import register_exception_handlers
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting application...")

    await es_client.info()
    await redis_client.ping()
    yield
    await es_client.close()
    await redis_client.aclose()
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
