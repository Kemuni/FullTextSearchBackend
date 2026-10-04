from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from elasticsearch import AsyncElasticsearch, dsl
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.elasticsearch import ElasticSearchContainer
from testcontainers.community.postgres import PostgresContainer

from app.api.deps import get_db
from app.core.db import Base
from app.documents import PostDocument
from app.main import app

ROOT_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    with PostgresContainer("postgres:18-alpine", driver="psycopg") as container:
        yield container


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg://", "postgresql+asyncpg://"
    )


@pytest.fixture
async def db_session(postgres_url: str) -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(scope="session")
def elasticsearch_container() -> Generator[ElasticSearchContainer]:
    container = (
        ElasticSearchContainer("elasticsearch:9.5.1")
        .with_env("discovery.type", "single-node")
        .with_env("xpack.security.enabled", "false")
        .with_env("ES_JAVA_OPTS", "-Xms512m -Xmx512m")
        .with_volume_mapping(
            ROOT_DIR / "elasticsearch-plugins.yml",
            "/usr/share/elasticsearch/config/elasticsearch-plugins.yml",
        )
    )
    with container:
        yield container


@pytest.fixture
async def elasticsearch_client(
    elasticsearch_container: ElasticSearchContainer,
) -> AsyncGenerator[AsyncElasticsearch]:
    client = AsyncElasticsearch(
        f"http://{elasticsearch_container.get_container_host_ip()}:"
        f"{elasticsearch_container.get_exposed_port(9200)}"
    )
    index = dsl.AsyncIndex(PostDocument.Index.name, using=client)
    if await index.exists():
        await index.delete()
    index.settings(**PostDocument.Index.settings)
    index.document(PostDocument)
    await index.create()
    try:
        yield client
    finally:
        await index.delete(ignore_unavailable=True)
        await client.close()


@pytest.fixture
def api_app(db_session: AsyncSession) -> Generator[FastAPI]:
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def api_client(api_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=api_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
