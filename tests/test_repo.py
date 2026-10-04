from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repo import DatabaseRepo
from app.models import OutboxAction, OutboxStatus, PostOutbox
from app.schemas import PostIn


async def test_is_posts_exist_and_get_methods(db_session: AsyncSession) -> None:
    repo = DatabaseRepo(db_session)
    assert await repo.is_posts_exist() is False

    created = await repo.create_or_update(PostIn(text="one", rubrics=["VK-1"]))

    assert await repo.is_posts_exist() is True
    assert [post.id for post in await repo.get_posts()] == [created.id]
    found = await repo.get_post(created.id)
    assert found is not None
    assert found.text == "one"
    assert await repo.get_post(999_999) is None


async def test_create_and_update_create_corresponding_outbox_events(
    db_session: AsyncSession,
) -> None:
    repo = DatabaseRepo(db_session)
    created = await repo.create_or_update(PostIn(text="before", rubrics=["VK-1"]))
    updated = await repo.create_or_update(
        PostIn(text="after", rubrics=["VK-2"]), post_id=created.id
    )
    outboxes = (
        (await db_session.execute(select(PostOutbox).order_by(PostOutbox.id)))
        .scalars()
        .all()
    )

    assert updated.id == created.id
    assert updated.text == "after"
    assert [(item.action, item.status) for item in outboxes] == [
        (OutboxAction.CREATE, OutboxStatus.PENDING),
        (OutboxAction.UPDATE, OutboxStatus.PENDING),
    ]
    assert outboxes[-1].payload == {
        "id": created.id,
        "text": "after",
        "rubrics": ["VK-2"],
    }


async def test_delete_post_creates_delete_outbox_event(
    db_session: AsyncSession,
) -> None:
    repo = DatabaseRepo(db_session)
    created = await repo.create_or_update(PostIn(text="delete me"))

    assert await repo.delete_post(created.id) is True
    assert await repo.get_post(created.id) is None
    assert await repo.delete_post(created.id) is False

    outbox = (
        (await db_session.execute(select(PostOutbox).order_by(PostOutbox.id.desc())))
        .scalars()
        .first()
    )
    assert outbox is not None
    assert outbox.action is OutboxAction.DELETE
    assert outbox.payload == {"id": created.id}


async def test_process_posts_batch_persists_all_posts(db_session: AsyncSession) -> None:
    repo = DatabaseRepo(db_session)

    posts = await repo.process_posts_batch(
        [PostIn(text="first", rubrics=["a"]), PostIn(text="second", rubrics=["b"])]
    )

    assert [post.text for post in posts] == ["first", "second"]
    assert len(await repo.get_posts()) == 2
