from elasticsearch import AsyncElasticsearch
from elasticsearch.dsl import async_connections

from app.core.config import settings
from app.documents import PostDocument

es_client = AsyncElasticsearch(
    hosts=[settings.ELASTICSEARCH_URL],
    verify_certs=False,
)
async_connections.add_connection("default", es_client)


DOCUMENTS = (PostDocument,)


async def create_es_indexes() -> None:
    """Создает все зарегистрированные индексы без изменения уже существующих"""
    for document in DOCUMENTS:
        if not await document._index.exists(using=es_client):
            await document.init(using=es_client)
