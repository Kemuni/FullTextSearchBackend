from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core import elasticsearch as elasticsearch_route
from app.documents import PostDocument
from app.models import Post


async def test_health_check_route(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/health-check/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_get_posts_and_get_post_routes(api_client: AsyncClient) -> None:
    created = await api_client.post(
        "/api/posts/", json={"text": "first", "rubrics": ["VK-1"]}
    )
    post_id = created.json()["data"]["id"]

    all_posts = await api_client.get("/api/posts/")
    found = await api_client.get(f"/api/posts/{post_id}")
    missing = await api_client.get("/api/posts/999999")

    assert all_posts.json()["data"]["data"][0]["id"] == post_id
    assert found.json()["data"]["text"] == "first"
    assert missing.status_code == 404
    assert missing.json() == {
        "success": False,
        "data": None,
        "errors": {"code": "http_404", "message": "Post not found"},
    }


async def test_create_and_update_post_routes(api_client: AsyncClient) -> None:
    created = await api_client.post(
        "/api/posts/", json={"text": "before", "rubrics": []}
    )
    post_id = created.json()["data"]["id"]
    updated = await api_client.put(
        f"/api/posts/{post_id}", json={"text": "after", "rubrics": ["VK-2"]}
    )
    invalid = await api_client.post("/api/posts/", json={"rubrics": []})

    assert created.status_code == 200
    assert updated.json()["data"]["id"] == post_id
    assert updated.json()["data"]["text"] == "after"
    assert updated.json()["data"]["rubrics"] == ["VK-2"]
    assert invalid.status_code == 422
    assert invalid.json()["errors"]["code"] == "validation_error"


async def test_delete_post_route(api_client: AsyncClient) -> None:
    created = await api_client.post("/api/posts/", json={"text": "remove"})
    post_id = created.json()["data"]["id"]

    deleted = await api_client.delete(f"/api/posts/{post_id}")
    missing = await api_client.delete(f"/api/posts/{post_id}")

    assert deleted.json() == {"success": True, "data": None, "errors": None}
    assert missing.status_code == 404


async def test_search_route_reads_documents_from_elasticsearch(
    api_client: AsyncClient, elasticsearch_client, monkeypatch
) -> None:
    now = datetime.now(UTC)
    document = PostDocument.from_post(
        Post(
            id=55,
            text="Привет ElasticSearch 🎁",
            rubrics=["VK-55", "news"],
            created_date=now,
            updated_at=now,
        )
    )
    second_document = PostDocument.from_post(
        Post(
            id=56,
            text="Привет ещё раз",
            rubrics=["VK-56"],
            created_date=now - timedelta(days=1),
            updated_at=now,
        )
    )

    async def documents():
        yield document
        yield second_document

    await PostDocument.bulk(documents(), using=elasticsearch_client, refresh="wait_for")
    monkeypatch.setattr(elasticsearch_route, "es_client", elasticsearch_client)

    response = await api_client.get(
        "/api/posts/search/",
        params={"query": "привет", "page_size": 1, "sort_by": "created_date"},
    )
    rubric_response = await api_client.get(
        "/api/posts/search/",
        params={
            "query": "привет",
            "rubrics": "VK-55",
            "created_from": (now - timedelta(seconds=1)).isoformat(),
        },
    )
    second_page = await api_client.get(
        "/api/posts/search/",
        params={
            "query": "привет",
            "page_size": 1,
            "sort_by": "created_date",
            "cursor": response.json()["data"]["next_cursor"],
        },
    )
    rubrics_response = await api_client.get(
        "/api/posts/rubrics/", params={"page_size": 1}
    )
    rubrics_second_page = await api_client.get(
        "/api/posts/rubrics/",
        params={
            "page_size": 1,
            "cursor": rubrics_response.json()["data"]["next_cursor"],
        },
    )
    invalid = await api_client.get("/api/posts/search/", params={"page_size": 101})

    assert response.status_code == 200
    assert response.json()["data"]["data"][0]["id"] == 55
    assert response.json()["data"]["next_cursor"] is not None
    assert rubric_response.json()["data"]["data"][0]["rubrics"] == ["VK-55", "news"]
    assert second_page.json()["data"]["data"][0]["id"] == 56
    assert rubrics_response.json()["data"]["data"] == ["VK-55"]
    assert rubrics_second_page.json()["data"]["data"] == ["VK-56"]
    assert invalid.status_code == 422
