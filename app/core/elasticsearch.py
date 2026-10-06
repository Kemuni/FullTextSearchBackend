import base64
import json
from ast import literal_eval
from datetime import datetime
from typing import Any, Literal

from elasticsearch import AsyncElasticsearch, dsl
from elasticsearch.dsl import Query, aggs, async_connections
from elasticsearch.dsl.aggs import Cardinality, Composite
from elasticsearch.dsl.query import Bool, MultiMatch, Range, Terms, Wildcard
from elasticsearch.dsl.types import WildcardQuery

from app.core.config import settings
from app.documents import PostDocument

es_client = AsyncElasticsearch(
    settings.ELASTICSEARCH_URL,
    verify_certs=False,
)
async_connections.add_connection("default", es_client)


INDEXES = (PostDocument,)


async def create_es_indexes() -> None:  # pragma: no cover
    """Создает все зарегистрированные индексы через публичный AsyncIndex API."""
    for document in INDEXES:
        index_meta = document.Index
        index_name = index_meta.name
        index_settings = index_meta.settings

        index = dsl.AsyncIndex(index_name, using=es_client)
        index.settings(**index_settings)
        index.document(document)
        if not await index.exists():
            await index.create()


def get_posts_index() -> dsl.AsyncIndex:  # pragma: no cover
    """Возвращает публичный DSL-объект индекса постов."""
    return dsl.AsyncIndex(PostDocument.Index.name, using=es_client)


class ElasticSearchRepo:
    PIT_KEEP_ALIVE = "1m"

    @staticmethod
    def _encode_cursor(pit_id: str, search_after: Any | None = None) -> str:
        """Кодирует Elasticsearch PIT и search_after в единый токен/курсор, которые безопасен в URL"""
        raw = json.dumps(
            {"pit_id": pit_id, "search_after": search_after},
            separators=(",", ":"),
            default=str,
        ).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[str, list[str] | None]:
        try:
            padded_cursor = cursor + "=" * (-len(cursor) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded_cursor))
        except Exception:
            raise ValueError("Invalid cursor")

        if not isinstance(payload, dict) or not isinstance(payload.get("pit_id"), str):
            raise ValueError("Invalid cursor")

        try:
            return payload["pit_id"], literal_eval(payload["search_after"])
        except KeyError:
            raise ValueError("Invalid cursor")

    @classmethod
    async def _open_pit_or_cursor(
        cls, cursor: str | None = None
    ) -> tuple[str, Any | None]:
        """
        При наличии курсора - читает его и достает данные, иначе открывает PIT.

        :raises ValueError: если курсор имеет неверный формат.
        :returns: tuple[str, list[str] | None] - pit_id и search_after (или None).
        """
        if cursor is not None:
            return cls._decode_cursor(cursor)
        else:
            pit = await es_client.open_point_in_time(
                index=PostDocument.Index.name, keep_alive=cls.PIT_KEEP_ALIVE
            )
            return pit["id"], None

    @classmethod
    def _parse_post_filters(
        cls,
        rubrics: list[str] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[Query]:
        filters: list[Query] = []
        if rubrics:
            filters.append(Terms(rubrics=rubrics))
        if created_from is not None or created_to is not None:
            date_range: dict[str, str] = {}
            if created_from is not None:
                date_range["gte"] = created_from.isoformat()
            if created_to is not None:
                date_range["lte"] = created_to.isoformat()
            filters.append(Range(created_date=date_range))
        return filters

    @classmethod
    def _parse_post_sort(
        cls,
        sort_by: Literal["relevance", "created_date"],
        sort_order: Literal["asc", "desc"],
    ) -> list[str | dict[str, dict[str, str]]]:
        if sort_by == "relevance":
            return [{"_score": {"order": sort_order}}, "-created_date", "-id"]
        else:
            return [
                f"{'-' if sort_order == 'desc' else ''}created_date",
                f"{'-' if sort_order == 'desc' else ''}id",
            ]

    @classmethod
    async def search_posts(
        cls,
        query: str = "",
        page_size: int = 50,
        cursor: str | None = None,
        rubrics: list[str] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: Literal["relevance", "created_date"] = "relevance",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[PostDocument], str | None, int]:
        """
        Проводит поиск по Elasticsearch по постам.

        :param query: Текст запроса.
        :param page_size: Размер страницы.
        :param cursor: Курсор страницы.
        :param rubrics: Фильтр по рубрикам.
        :param created_from: Создан с.
        :param created_to: Создан до.
        :param sort_by: Сортировка по "релевантности" или "дате создания".
        :param sort_order: Настройка сортировки.
        :return: Список постов, новый курсор и общее количество найденных постов.
        """
        pit_id, search_after = await cls._open_pit_or_cursor(cursor)

        query = query.strip()
        search = (
            PostDocument.search(using=es_client)
            .query(
                Bool(
                    must=[
                        Bool(
                            should=[
                                MultiMatch(
                                    query=query, fields=["text"], fuzziness="AUTO"
                                ),
                                Wildcard(rubrics=WildcardQuery(value=f"*{query}*")),
                            ],
                            minimum_should_match=1,
                        ),
                    ],
                    filter=cls._parse_post_filters(rubrics, created_from, created_to),
                )
            )
            .sort(*cls._parse_post_sort(sort_by, sort_order))
            .extra(track_total_hits=True)
            .index()
            .extra(pit={"id": pit_id, "keep_alive": cls.PIT_KEEP_ALIVE})[:page_size]
        )
        if search_after is not None:
            search = search.extra(search_after=search_after)

        response = await search.execute()

        hits = response.hits
        total_hits = response.hits.total.value  # type: ignore
        search_after = response.hits[-1].meta.sort if hits else None

        return (
            hits,
            cls._encode_cursor(pit_id=pit_id, search_after=search_after)
            if hits
            else None,
            total_hits,
        )

    @classmethod
    async def get_rubrics(
        cls, page_size: int = 50, cursor: str | None = None
    ) -> tuple[list[dict], str | None, int]:
        """Получение уникальных рубрик с пагинацией"""
        pit_id, after_key = await cls._open_pit_or_cursor(cursor)

        search = PostDocument.search(using=es_client)[:page_size]
        if after_key:
            search.aggs.bucket(
                "rubrics",
                Composite(
                    sources=[{"rubric": aggs.Terms(field="rubrics")}],
                    after=after_key,
                    size=page_size,
                ),
            )
        else:
            search.aggs.bucket(
                "rubrics",
                Composite(
                    sources=[{"rubric": aggs.Terms(field="rubrics")}], size=page_size
                ),
            )
        search.aggs.bucket(
            "unique_count", Cardinality(field="rubrics", precision_threshold=30_000)
        )
        search.index().extra(pit={"id": pit_id, "keep_alive": cls.PIT_KEEP_ALIVE})

        response = await search.execute()
        buckets = response.aggregations.rubrics.buckets
        after_key = response.aggregations.rubrics.after_key

        next_cursor = (
            cls._encode_cursor(pit_id=pit_id, search_after=after_key)
            if buckets
            else None
        )

        return (
            [bucket.key.rubric for bucket in buckets],
            next_cursor,
            response.aggregations.unique_count.value,
        )
