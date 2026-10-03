import csv
import logging
from itertools import islice

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.repo import DatabaseRepo
from app.schemas import PostIn

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


async def fill_init_data():
    """Заполнение БД начальными данными"""
    logger.info("Filling init data...")
    with open(str(settings.INIT_DATA_PATH)) as f:
        reader = csv.DictReader(f)
        async with async_session_maker() as session:
            repo = DatabaseRepo(session)
            if await repo.is_posts_exist():
                logger.info("Found posts, skipping init data")
                return

            while batch := list(islice(reader, BATCH_SIZE)):
                await process_batch(session, batch)
    logger.info("Init data filled")


async def process_batch(session: AsyncSession, batch: list[dict]) -> None:
    repo = DatabaseRepo(session)
    logger.info(f"Filling batch: {len(batch)} posts")
    await repo.process_posts_batch([PostIn(**post) for post in batch])
    logger.info(f"Batch filled: {len(batch)} posts")
