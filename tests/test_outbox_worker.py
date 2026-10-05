import asyncio

import pytest
from elasticsearch import AsyncElasticsearch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.repo import DatabaseRepo
from app.models import OutboxStatus, PostOutbox
from app.schemas import PostIn
from app.tasks.outbox_worker import OutboxWorker


def get_worker(
    db_session: AsyncSession,
    elasticsearch_client: AsyncElasticsearch,
    batch_size: int = 100,
) -> OutboxWorker:
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    return OutboxWorker(session_factory, elasticsearch_client, batch_size)


async def get_outboxes(db_session: AsyncSession) -> list[PostOutbox]:
    db_session.expire_all()
    return list(
        (await db_session.execute(select(PostOutbox).order_by(PostOutbox.id)))
        .scalars()
        .all()
    )


async def test_worker_indexes_create_and_update_events(
    db_session: AsyncSession, elasticsearch_client: AsyncElasticsearch
) -> None:
    repo = DatabaseRepo(db_session)
    created = await repo.create_or_update(PostIn(text="before", rubrics=["VK-1"]))
    worker = get_worker(db_session, elasticsearch_client)

    assert await worker.process_one_batch() == 1
    indexed = await elasticsearch_client.get(index="posts", id=str(created.id))
    assert indexed["_source"]["text"] == "before"

    await repo.create_or_update(
        PostIn(text="after 👋", rubrics=["VK-2"]), post_id=created.id
    )
    assert await worker.process_one_batch() == 1
    indexed = await elasticsearch_client.get(index="posts", id=str(created.id))

    assert indexed["_source"]["text"] == "after 👋"
    assert indexed["_source"]["rubrics"] == ["VK-2"]
    assert all(
        event.status is OutboxStatus.COMPLETED
        for event in await get_outboxes(db_session)
    )
    assert all(
        event.processed_at is not None for event in await get_outboxes(db_session)
    )


async def test_worker_deletes_document_for_delete_event(
    db_session: AsyncSession, elasticsearch_client: AsyncElasticsearch
) -> None:
    repo = DatabaseRepo(db_session)
    post = await repo.create_or_update(PostIn(text="delete", rubrics=[]))
    worker = get_worker(db_session, elasticsearch_client)
    await worker.process_one_batch()

    assert await repo.delete_post(post.id) is True
    assert await worker.process_one_batch() == 1

    assert not await elasticsearch_client.exists(index="posts", id=str(post.id))
    assert (await get_outboxes(db_session))[-1].status is OutboxStatus.COMPLETED


async def test_concurrent_workers_claim_distinct_events(
    db_session: AsyncSession, elasticsearch_client: AsyncElasticsearch
) -> None:
    repo = DatabaseRepo(db_session)
    first = await repo.create_or_update(PostIn(text="one", rubrics=[]))
    second = await repo.create_or_update(PostIn(text="two", rubrics=[]))
    first_worker = get_worker(db_session, elasticsearch_client, batch_size=1)
    second_worker = get_worker(db_session, elasticsearch_client, batch_size=1)

    processed = await asyncio.gather(
        first_worker.process_one_batch(), second_worker.process_one_batch()
    )

    assert sorted(processed) == [1, 1]
    assert await elasticsearch_client.exists(index="posts", id=str(first.id))
    assert await elasticsearch_client.exists(index="posts", id=str(second.id))
    assert [event.status for event in await get_outboxes(db_session)] == [
        OutboxStatus.COMPLETED,
        OutboxStatus.COMPLETED,
    ]


async def test_failed_delivery_rolls_back_outbox_to_pending(
    db_session: AsyncSession, elasticsearch_client: AsyncElasticsearch, monkeypatch
) -> None:
    repo = DatabaseRepo(db_session)
    await repo.create_or_update(PostIn(text="retry", rubrics=[]))
    worker = get_worker(db_session, elasticsearch_client)

    async def fail_delivery(_: list[PostOutbox]) -> None:
        raise RuntimeError("Elasticsearch is unavailable")

    monkeypatch.setattr(worker, "_send_to_elasticsearch", fail_delivery)

    with pytest.raises(RuntimeError, match="unavailable"):
        await worker.process_one_batch()

    [event] = await get_outboxes(db_session)
    assert event.status is OutboxStatus.PENDING
    assert event.processed_at is None


async def test_no_pending_outboxes(
    db_session: AsyncSession, elasticsearch_client: AsyncElasticsearch
) -> None:
    worker = get_worker(db_session, elasticsearch_client)

    assert len(await get_outboxes(db_session)) == 0
    assert await worker.process_one_batch() == 0
