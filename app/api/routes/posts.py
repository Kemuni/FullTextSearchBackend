from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.base import APIResponseRouter
from app.api.deps import get_db
from app.core.elasticsearch import es_client
from app.core.repo import DatabaseRepo
from app.documents import PostDocument
from app.schemas import PostIn, PostPublic, SuccessResponse

router = APIResponseRouter(prefix="/posts", tags=["posts"])


@router.get(
    "/",
    response_model=SuccessResponse[list[PostPublic]],
)
async def get_posts(db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    return SuccessResponse(data=list(await repo.get_posts()))


@router.get(
    "/search/",
    response_model=SuccessResponse[list[PostPublic]],
)
async def search_posts(
    query: Annotated[str, Query(min_length=1, max_length=500)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
):
    search = (
        PostDocument.search(using=es_client)
        .query("multi_match", query=query, fields=["text"])
        .extra(size=limit)
    )
    response = await search.execute()
    post_ids = [int(hit.meta.id) for hit in response.hits]

    repo = DatabaseRepo(db)
    posts_by_id = {post.id: post for post in await repo.get_posts_by_ids(post_ids)}
    return SuccessResponse(
        data=[posts_by_id[post_id] for post_id in post_ids if post_id in posts_by_id]
    )


@router.get(
    "/{post_id}",
    response_model=SuccessResponse[PostPublic],
)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    db_post = await repo.get_post(post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return SuccessResponse(data=db_post)


@router.post(
    "/",
    response_model=SuccessResponse[PostPublic],
)
async def create_post(post_in: PostIn, db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    return SuccessResponse(data=await repo.create_or_update(post_in))


@router.put(
    "/{post_id}",
    response_model=SuccessResponse[PostPublic],
)
async def update_post(
    post_id: int, post_in: PostIn, db: AsyncSession = Depends(get_db)
):
    repo = DatabaseRepo(db)
    return SuccessResponse(
        data=PostPublic.model_validate(
            await repo.create_or_update(post_in, post_id=post_id)
        )
    )


@router.delete(
    "/{post_id}",
    response_model=SuccessResponse,
)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    is_success = await repo.delete_post(post_id)
    if not is_success:
        raise HTTPException(status_code=404, detail="Post not found")
    return SuccessResponse(data=None)
