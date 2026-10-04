from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxAction, OutboxStatus, Post, PostOutbox
from app.schemas import PostIn


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

    async def get_posts_after_id(self, after_id: int, limit: int) -> Sequence[Post]:
        query = select(Post).where(Post.id > after_id).order_by(Post.id).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_posts_by_ids(self, post_ids: list[int]) -> Sequence[Post]:
        if not post_ids:
            return []
        query = select(Post).where(Post.id.in_(post_ids))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_post(self, post_id: int) -> Post | None:
        query = select(Post).where(Post.id == post_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_or_update(
        self, post_in: PostIn, post_id: int | None = None
    ) -> Post:
        post = Post(id=post_id, **post_in.model_dump())
        db_post = await self.db.merge(post)
        await self.db.flush()
        outbox = PostOutbox(
            payload={"id": db_post.id, **post_in.model_dump()},
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

    async def process_posts_batch(
        self, batch: list[PostIn], *, commit: bool = True
    ) -> None:
        db_posts = [Post(**post.model_dump()) for post in batch]
        self.db.add_all(db_posts)
        await self.db.flush()
        db_outbox = [
            PostOutbox(
                payload={"id": db_post.id, **post_in.model_dump()},
                status=OutboxStatus.PENDING,
                action=OutboxAction.CREATE,
            )
            for db_post, post_in in zip(db_posts, batch, strict=False)
        ]
        self.db.add_all(db_outbox)
        if commit:
            await self.db.commit()
