import csv
import logging
from ast import literal_eval
from datetime import datetime
from itertools import islice

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.elasticsearch import es_client, get_posts_index
from app.core.repo import DatabaseRepo
from app.documents import PostDocument
from app.schemas import InitPostIn

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


async def fill_init_data() -> None:
    """Заполняет Postgres и Elasticsearch из CSV в одних и тех же батчах."""
    logger.info("Filling init data...")
    async with async_session_maker() as session:
        repo = DatabaseRepo(session)
        if await repo.is_posts_exist():
            logger.info("Found posts, skipping init data")
            return

        with settings.INIT_DATA_PATH.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            while batch := list(islice(reader, BATCH_SIZE)):
                await process_batch(session, batch)
    await get_posts_index().refresh()
    logger.info("Init data filled")


def process_csv_post_to_schema(csv_post: dict) -> InitPostIn:
    return InitPostIn(
        text=csv_post["text"],
        created_date=datetime.strptime(csv_post["created_date"], "%Y-%m-%d %H:%M:%S"),
        updated_at=datetime.strptime(csv_post["created_date"], "%Y-%m-%d %H:%M:%S"),
        rubrics=[str(rubric) for rubric in literal_eval(csv_post["rubrics"])],
    )


async def process_batch(session: AsyncSession, batch: list[dict]) -> None:
    repo = DatabaseRepo(session)
    logger.info(f"Filling batch: {len(batch)} posts")
    db_posts = await repo.process_posts_batch(
        [process_csv_post_to_schema(csv_post) for csv_post in batch]
    )

    async def documents():
        for post in db_posts:
            yield PostDocument.from_post(post)

    await PostDocument.bulk(documents(), using=es_client)
    logger.info(f"Batch filled: {len(batch)} posts")
