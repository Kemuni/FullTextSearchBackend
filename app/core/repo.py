from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxAction, OutboxStatus, Post, PostOutbox
from app.schemas import InitPostIn, PostIn


class DatabaseRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_posts_exist(self) -> bool:
        query = select(exists().select_from(Post))
        result = await self.db.execute(query)
        return bool(result.scalar_one())

    async def get_posts(self) -> Sequence[Post]:
        query = select(Post)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_post(self, post_id: int) -> Post | None:
        query = select(Post).where(Post.id == post_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def lock_pending_outboxes(self, limit: int) -> Sequence[PostOutbox]:
        """Берет доступные Outbox события с блокировкой"""
        now = datetime.now(UTC)
        query = (
            select(PostOutbox)
            .where(
                PostOutbox.status == OutboxStatus.PENDING,
                or_(
                    PostOutbox.next_attempt_at.is_(None),
                    PostOutbox.next_attempt_at <= now,
                ),
            )
            .order_by(PostOutbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = list((await self.db.execute(query)).scalars().all())
        return events

    async def create_or_update(
        self, post_in: PostIn, post_id: int | None = None
    ) -> Post:
        post = Post(id=post_id, **post_in.model_dump())
        db_post = await self.db.merge(post)
        await self.db.flush()
        outbox = PostOutbox(
            payload={
                "id": db_post.id,
                **post_in.model_dump(),
                "created_date": str(db_post.created_date),
                "updated_at": str(datetime.now(tz=UTC)),
            },
            status=OutboxStatus.PENDING,
            action=OutboxAction.CREATE if post_id is None else OutboxAction.UPDATE,
        )
        self.db.add(outbox)
        await self.db.commit()
        await self.db.refresh(db_post)
        return db_post

    async def delete_post(self, post_id: int) -> bool:
        post = await self.get_post(post_id)
        if post is None:
            return False
        await self.db.delete(post)
        outbox = PostOutbox(
            payload={"id": post_id},
            status=OutboxStatus.PENDING,
            action=OutboxAction.DELETE,
        )
        self.db.add(outbox)
        await self.db.commit()
        return True

    async def process_posts_batch(self, batch: list[InitPostIn]) -> list[Post]:
        db_posts = [Post(**post.model_dump()) for post in batch]
        self.db.add_all(db_posts)
        await self.db.commit()
        return db_posts
