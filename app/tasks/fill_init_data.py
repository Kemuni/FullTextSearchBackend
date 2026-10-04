import csv
import logging
from itertools import islice

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.elasticsearch import es_client
from app.core.repo import DatabaseRepo
from app.documents import PostDocument
from app.schemas import PostIn

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


async def fill_init_data() -> None:
    """Идемпотентно заполняет Postgres и синхронизирует начальные данные с ES"""
    logger.info("Filling init data...")
    async with async_session_maker() as session:
        repo = DatabaseRepo(session)
        if await repo.is_posts_exist():
            logger.info("Found posts, skipping Postgres init data")
        else:
            with settings.INIT_DATA_PATH.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                while batch := list(islice(reader, BATCH_SIZE)):
                    await process_batch(session, batch, commit=False)

    async with async_session_maker() as session:
        repo = DatabaseRepo(session)
        indexed_count = await sync_posts_to_elasticsearch(repo)
    logger.info(
        "Init data filled; synchronized %s posts to Elasticsearch", indexed_count
    )


async def sync_posts_to_elasticsearch(repo: DatabaseRepo) -> int:
    """Повторно записывает документы с _id=id Postgres без создания дубликатов"""

    async def documents():
        last_id = 0
        while posts := await repo.get_posts_after_id(last_id, BATCH_SIZE):
            for post in posts:
                yield PostDocument.from_post(post)
            last_id = posts[-1].id

    indexed_count, _ = await PostDocument.bulk(
        documents(),
        using=es_client,
        refresh="wait_for",
    )
    return indexed_count


async def process_batch(
    session: AsyncSession, batch: list[dict], *, commit: bool = True
) -> None:
    repo = DatabaseRepo(session)
    logger.info(f"Filling batch: {len(batch)} posts")
    await repo.process_posts_batch([PostIn(**post) for post in batch], commit=commit)
    logger.info(f"Batch filled: {len(batch)} posts")
