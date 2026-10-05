import datetime
from typing import Self

from elasticsearch import dsl

from app.models import Post
from app.schemas import OutboxPostPayload


class PostDocument(dsl.AsyncDocument):
    id: int = dsl.mapped_field(dsl.Keyword())
    text: str = dsl.mapped_field(dsl.Text(analyzer="multilingual_analyzer"))
    rubrics: list[str] = dsl.mapped_field(dsl.Keyword())

    created_date: datetime.datetime = dsl.mapped_field(dsl.Date())
    updated_at: datetime.datetime = dsl.mapped_field(dsl.Date())

    @classmethod
    def from_post(cls, post: Post) -> Self:
        """Создает ES документ на основе модели Post из Postgres"""
        document = cls(
            id=post.id,
            text=post.text,
            rubrics=post.rubrics,
            created_date=post.created_date,
            updated_at=post.updated_at,
        )
        document.meta.id = str(post.id)
        return document

    @classmethod
    def from_outbox_payload(cls, payload: OutboxPostPayload) -> Self:
        """Создает ES-документ из проверенного payload Outbox-события."""
        document = cls(
            id=payload.id,
            text=payload.text,
            rubrics=payload.rubrics,
            created_date=payload.created_date,
            updated_at=payload.updated_at,
        )
        document.meta.id = str(document.id)
        return document

    class Index:
        name = "posts"
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "multilingual_analyzer": {
                        "type": "custom",
                        "tokenizer": "icu_tokenizer",
                        "filter": ["icu_normalizer", "icu_folding", "lowercase"],
                    }
                }
            },
        }
