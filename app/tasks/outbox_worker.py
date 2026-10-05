import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime
from typing import Any

from elasticsearch import AsyncElasticsearch
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.db import async_session_maker
from app.core.elasticsearch import es_client
from app.core.repo import DatabaseRepo
from app.documents import PostDocument
from app.models import OutboxAction, OutboxStatus, PostOutbox
from app.schemas import OutboxPostPayload

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Доставляет события Outbox в Elasticsearch"""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = async_session_maker,
        elasticsearch_client: AsyncElasticsearch = es_client,
        batch_size: int = settings.OUTBOX_BATCH_SIZE,
    ) -> None:
        self.session_factory = session_factory
        self.elasticsearch_client = elasticsearch_client
        self.batch_size = batch_size

    async def process_one_batch(self) -> int:
        """Обрабатывает один батч с блокировкой рядов в БД для исключения конкуренцию"""
        async with self.session_factory.begin() as session:
            events = await DatabaseRepo(session).lock_pending_outboxes(self.batch_size)
            if not events:
                return 0

            await self._send_to_elasticsearch(events)
            processed_at = datetime.now(UTC)
            for event in events:
                event.status = OutboxStatus.COMPLETED
                event.processed_at = processed_at
        return len(events)

    async def _send_to_elasticsearch(self, events: Sequence[PostOutbox]) -> None:
        async def actions() -> AsyncGenerator[PostDocument | dict[str, Any], None]:
            for event in events:
                if event.action is OutboxAction.DELETE:
                    yield {"_op_type": "delete", "_id": str(event.payload["id"])}
                else:
                    try:
                        yield PostDocument.from_outbox_payload(
                            OutboxPostPayload(**event.payload)
                        )
                    except ValidationError:
                        logger.exception(
                            f"Incorrect payload of Outbox event (Event ID={event.id}): {event.payload}"
                        )

        await PostDocument.bulk(actions(), using=self.elasticsearch_client)

    async def run_forever(self) -> None:  # pragma: no cover
        while True:
            try:
                processed = await self.process_one_batch()
            except Exception as e:
                logger.exception(f"Failed to process Outbox batch: {e}")
                await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SECONDS)
                continue

            if processed == 0:
                await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SECONDS)


async def main() -> None:  # pragma: no cover
    worker = OutboxWorker()
    try:
        await es_client.info()
        await worker.run_forever()
    finally:
        await es_client.close()


if __name__ == "__main__":
    asyncio.run(main())
