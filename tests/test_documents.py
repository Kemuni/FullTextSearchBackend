from datetime import UTC, datetime

from elasticsearch.dsl.query import Match

from app.documents import PostDocument
from app.models import Post


async def test_post_document_is_indexed_and_searchable(
    elasticsearch_client,
) -> None:
    now = datetime.now(UTC)
    post = Post(
        id=42,
        text="Привет ElasticSearch 🎁 English",
        rubrics=["VK-42"],
        created_date=now,
        updated_at=now,
    )
    document = PostDocument.from_post(post)

    async def documents():
        yield document

    success_count, _ = await PostDocument.bulk(
        documents(), using=elasticsearch_client, refresh="wait_for"
    )
    response = await (
        PostDocument.search(using=elasticsearch_client)
        .query(Match(text="привет"))
        .execute()
    )

    assert success_count == 1
    assert document.meta.id == "42"
    assert response.hits[0].to_dict()["text"] == post.text


def test_post_document_has_unicode_aware_analyzer() -> None:
    analyzer = PostDocument.Index.settings["analysis"]["analyzer"][  # type: ignore
        "multilingual_analyzer"
    ]

    assert analyzer["tokenizer"] == "icu_tokenizer"
    assert {"icu_normalizer", "icu_folding", "lowercase"} <= set(analyzer["filter"])
