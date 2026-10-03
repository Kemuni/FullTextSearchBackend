from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Post
from app.schemas import PostIn


class DatabaseRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_posts(self) -> Sequence[Post]:
        query = select(Post)
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
        await self.db.commit()
        return db_post

    async def delete_post(self, post_id: int) -> bool:
        post = await self.get_post(post_id)
        if post is None:
            return False
        await self.db.delete(post)
        await self.db.commit()
        return True
