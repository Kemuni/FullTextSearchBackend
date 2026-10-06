from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.base import APIResponseRouter
from app.api.deps import get_db
from app.core.config import settings
from app.core.elasticsearch import ElasticSearchRepo
from app.core.redis import (
    delete_cached_value,
    get_cached_value,
    read_rate_limit,
    set_cached_value,
    write_rate_limit,
)
from app.core.repo import DatabaseRepo
from app.schemas import (
    PaginatedResponse,
    PostIn,
    PostPublic,
    PostSearchQuery,
    SearchResponse,
    SuccessResponse,
)

router = APIResponseRouter(prefix="/posts", tags=["posts"])
POST_CACHE_KEY_PREFIX = "post"


def _post_cache_key(post_id: int) -> str:
    return f"{POST_CACHE_KEY_PREFIX}:{post_id}"


@router.get(
    "/",
    summary="Получение списка постов с пагинацией по БД PostgreSQL",
    response_model=SuccessResponse[PaginatedResponse[PostPublic]],
    dependencies=[Depends(read_rate_limit)],
)
async def get_posts(
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    repo = DatabaseRepo(db)
    total_posts = await repo.get_posts_amount()
    total_pages = total_posts // page_size + (1 if total_posts % page_size > 0 else 0)

    if page > total_pages:
        raise HTTPException(status_code=400, detail="Page out of range")

    posts = await repo.get_posts(page_size, (page - 1) * page_size)
    return SuccessResponse(
        data=PaginatedResponse(
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=list(posts),
        )
    )


@router.get(
    "/search/",
    summary="Получение списка постов с пагинацией через ElasticSearch",
    response_model=SuccessResponse[SearchResponse[PostPublic]],
    dependencies=[Depends(read_rate_limit)],
)
async def search_posts(filter_query: Annotated[PostSearchQuery, Query()]):
    hits, next_cursor, total_hits = await ElasticSearchRepo.search_posts(
        query=filter_query.query,
        page_size=filter_query.page_size,
        cursor=filter_query.cursor,
        rubrics=filter_query.rubrics,
        created_from=filter_query.created_from,
        created_to=filter_query.created_to,
        sort_by=filter_query.sort_by,
        sort_order=filter_query.sort_order,
    )

    return SuccessResponse(
        data=SearchResponse(
            page_size=filter_query.page_size,
            total=total_hits,
            old_cursor=filter_query.cursor,
            next_cursor=next_cursor,
            data=[PostPublic.model_validate(hit) for hit in hits],
        )
    )


@router.get(
    "/rubrics/",
    summary="Получение списка уникальных rubrics с пагинацией через ElasticSearch",
    response_model=SuccessResponse[SearchResponse[str]],
    dependencies=[Depends(read_rate_limit)],
)
async def get_rubrics(
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Количество элементов на странице")
    ] = 50,
    cursor: Annotated[str | None, Query(description="Курсор для пагинации")] = None,
):
    buckets, next_cursor, total = await ElasticSearchRepo.get_rubrics(
        page_size=page_size, cursor=cursor
    )

    return SuccessResponse(
        data=SearchResponse(
            page_size=page_size,
            old_cursor=cursor,
            total=total,
            next_cursor=next_cursor,
            data=buckets,
        )
    )


@router.get(
    "/{post_id}",
    summary="Получения поста по ID",
    response_model=SuccessResponse[PostPublic],
    dependencies=[Depends(read_rate_limit)],
)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    cached_post = await get_cached_value(_post_cache_key(post_id))
    if cached_post is not None:
        return SuccessResponse(data=PostPublic.model_validate_json(cached_post))

    repo = DatabaseRepo(db)
    db_post = await repo.get_post(post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    post = PostPublic.model_validate(db_post)
    await set_cached_value(
        _post_cache_key(post_id),
        post.model_dump_json(),
        settings.POST_CACHE_TTL_SECONDS,
    )
    return SuccessResponse(data=post)


@router.post(
    "/",
    summary="Добавление нового поста",
    response_model=SuccessResponse[PostPublic],
    dependencies=[Depends(write_rate_limit)],
)
async def create_post(post_in: PostIn, db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    post = await repo.create_or_update(post_in)
    await delete_cached_value(_post_cache_key(post.id))
    return SuccessResponse(data=post)


@router.put(
    "/{post_id}",
    summary="Изменение созданного поста",
    response_model=SuccessResponse[PostPublic],
    dependencies=[Depends(write_rate_limit)],
)
async def update_post(
    post_id: int, post_in: PostIn, db: AsyncSession = Depends(get_db)
):
    repo = DatabaseRepo(db)
    post = PostPublic.model_validate(
        await repo.create_or_update(post_in, post_id=post_id)
    )
    await delete_cached_value(_post_cache_key(post_id))
    return SuccessResponse(data=post)


@router.delete(
    "/{post_id}",
    summary="Удаление существующего поста",
    response_model=SuccessResponse,
    dependencies=[Depends(write_rate_limit)],
)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    repo = DatabaseRepo(db)
    is_success = await repo.delete_post(post_id)
    if not is_success:
        raise HTTPException(status_code=404, detail="Post not found")
    await delete_cached_value(_post_cache_key(post_id))
    return SuccessResponse(data=None)
