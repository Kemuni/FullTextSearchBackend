from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Post


class DatabaseRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_posts(self) -> Sequence[Post]:
        query = select(Post)
        result = await self.db.execute(query)
        return result.scalars().all()
