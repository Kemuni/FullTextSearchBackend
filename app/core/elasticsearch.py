from elasticsearch import AsyncElasticsearch, dsl
from elasticsearch.dsl import async_connections

from app.core.config import settings
from app.documents import PostDocument

es_client = AsyncElasticsearch(
    settings.ELASTICSEARCH_URL,
    verify_certs=False,
)
async_connections.add_connection("default", es_client)


INDEXES = (PostDocument,)


async def create_es_indexes() -> None:
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


def get_posts_index() -> dsl.AsyncIndex:
    """Возвращает публичный DSL-объект индекса постов."""
    return dsl.AsyncIndex(PostDocument.Index.name, using=es_client)
