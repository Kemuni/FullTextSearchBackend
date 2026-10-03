from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.base import APIResponseRouter
from app.api.deps import get_db
from app.core.repo import DatabaseRepo
from app.schemas import PostPublic, SuccessResponse

router = APIResponseRouter(prefix="/posts", tags=["posts"])


@router.get(
    "/",
    response_model=SuccessResponse[list[PostPublic]],
)
async def get_posts(db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    return SuccessResponse(data=list(await repo.get_posts()))
