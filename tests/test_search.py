"""Search endpoint and vector store tests."""

from types import SimpleNamespace

from app.services.vector_store_service import VectorStoreService


def test_text_search_response_schema(client) -> None:
    response = client.post("/api/v1/search/text", json={"query": "main revenue drivers", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "main revenue drivers"
    assert data["results"][0]["citation"] == "sample.pdf, page 1"
    assert data["results"][0]["content_type"] == "text"


def test_image_search_response_schema(client) -> None:
    response = client.post("/api/v1/search/images", json={"query": "bar chart revenue", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["content_type"] == "image"
    assert data["results"][0]["citation"] == "sample.pdf, page 2, image 1"


def test_multimodal_search_keeps_result_sets_separate(client) -> None:
    response = client.post("/api/v1/search/multimodal", json={"query": "revenue", "top_k": 2})
    assert response.status_code == 200
    data = response.json()
    assert "text_results" in data
    assert "image_results" in data


def test_qdrant_service_search_uses_payload_mapping(monkeypatch) -> None:
    service = VectorStoreService()

    class FakeClient:
        def search(self, **kwargs):
            assert kwargs["collection_name"] == service.settings.qdrant_text_collection
            return [
                SimpleNamespace(
                    score=0.77,
                    payload={
                        "document_id": "doc-1",
                        "document_name": "report.pdf",
                        "page_number": 3,
                        "chunk_id": "chunk-1",
                        "chunk_index": 0,
                        "text": "A cited chunk",
                        "content_type": "text",
                        "citation": "report.pdf, page 3",
                        "extraction_status": "extracted",
                    },
                )
            ]

    monkeypatch.setattr(service, "_client", FakeClient())
    results = service.search_text([0.1] * service.settings.text_embedding_dimension, 1)
    assert results[0].score == 0.77
    assert results[0].citation == "report.pdf, page 3"
