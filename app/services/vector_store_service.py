"""Qdrant vector store integration."""

from typing import Any

from fastapi import status

from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode
from app.schemas.search import ImageSearchResult, TextSearchResult
from app.services.chunking_service import TextChunk
from app.services.pdf_service import ExtractedImage


class VectorStoreService:
    """Manage Qdrant collections, upserts, searches, and deletion."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Return a lazily constructed Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self.settings.qdrant_url, timeout=int(self.settings.qdrant_timeout_seconds)
                )
            except Exception as exc:
                raise AppError(
                    ErrorCode.QDRANT_UNAVAILABLE,
                    "Qdrant client could not be initialized",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc
        return self._client

    def initialize_collections(self) -> None:
        """Create separate text and image collections if they do not exist."""
        try:
            from qdrant_client import models

            self._ensure_collection(
                self.settings.qdrant_text_collection,
                self.settings.text_embedding_dimension,
                models.Distance.COSINE,
            )
            self._ensure_collection(
                self.settings.qdrant_image_collection,
                self.settings.image_embedding_dimension,
                models.Distance.COSINE,
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                ErrorCode.QDRANT_UNAVAILABLE,
                "Qdrant is unavailable",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _ensure_collection(self, collection_name: str, dimension: int, distance: Any) -> None:
        from qdrant_client import models

        if self.client.collection_exists(collection_name=collection_name):
            return
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=dimension, distance=distance),
        )

    def upsert_text_chunks(self, chunks: list[TextChunk], vectors: list[list[float]]) -> None:
        """Batch upsert text chunk vectors."""
        if len(chunks) != len(vectors):
            raise AppError(ErrorCode.EMBEDDING_FAILURE, "Text chunk/vector count mismatch")
        if not chunks:
            return
        try:
            from qdrant_client import models

            points = [
                models.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload={
                        "document_id": chunk.document_id,
                        "document_name": chunk.document_name,
                        "page_number": chunk.page_number,
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "content_type": chunk.content_type,
                        "citation": chunk.citation,
                        "extraction_status": "extracted",
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            self.client.upsert(collection_name=self.settings.qdrant_text_collection, points=points)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorCode.QDRANT_UNAVAILABLE, "Failed to upsert text vectors") from exc

    def upsert_images(self, document_name: str, images: list[ExtractedImage], vectors: list[list[float]]) -> None:
        """Batch upsert extracted image vectors."""
        if len(images) != len(vectors):
            raise AppError(ErrorCode.EMBEDDING_FAILURE, "Image/vector count mismatch")
        if not images:
            return
        try:
            from qdrant_client import models

            points = [
                models.PointStruct(
                    id=image.image_id,
                    vector=vector,
                    payload={
                        "document_id": image.document_id,
                        "document_name": document_name,
                        "page_number": image.page_number,
                        "image_id": image.image_id,
                        "image_index": image.image_index,
                        "image_path": str(image.image_path),
                        "width": image.width,
                        "height": image.height,
                        "content_type": image.content_type,
                        "citation": f"{document_name}, page {image.page_number}, image {image.image_index}",
                        "extraction_status": image.extraction_status,
                    },
                )
                for image, vector in zip(images, vectors, strict=True)
            ]
            self.client.upsert(collection_name=self.settings.qdrant_image_collection, points=points)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorCode.QDRANT_UNAVAILABLE, "Failed to upsert image vectors") from exc

    def search_text(
        self, query_vector: list[float], top_k: int, document_id: str | None = None
    ) -> list[TextSearchResult]:
        """Search the text collection."""
        hits = self._search(self.settings.qdrant_text_collection, query_vector, top_k, document_id)
        return [
            TextSearchResult(
                score=float(hit.score),
                document_id=str(hit.payload["document_id"]),
                document_name=str(hit.payload["document_name"]),
                page_number=int(hit.payload["page_number"]),
                chunk_id=str(hit.payload["chunk_id"]),
                chunk_index=int(hit.payload["chunk_index"]),
                text=str(hit.payload["text"]),
                content_type=str(hit.payload["content_type"]),
                citation=str(hit.payload["citation"]),
                extraction_status=str(hit.payload.get("extraction_status", "extracted")),
            )
            for hit in hits
        ]

    def search_images(
        self,
        query_vector: list[float],
        top_k: int,
        document_id: str | None = None,
    ) -> list[ImageSearchResult]:
        """Search the image collection."""
        hits = self._search(self.settings.qdrant_image_collection, query_vector, top_k, document_id)
        return [
            ImageSearchResult(
                score=float(hit.score),
                document_id=str(hit.payload["document_id"]),
                document_name=str(hit.payload["document_name"]),
                page_number=int(hit.payload["page_number"]),
                image_id=str(hit.payload["image_id"]),
                image_index=int(hit.payload["image_index"]),
                image_path=str(hit.payload["image_path"]),
                width=int(hit.payload["width"]),
                height=int(hit.payload["height"]),
                content_type=str(hit.payload["content_type"]),
                citation=str(hit.payload["citation"]),
                extraction_status=str(hit.payload.get("extraction_status", "extracted")),
            )
            for hit in hits
        ]

    def _search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        document_id: str | None,
    ) -> list[Any]:
        try:
            return list(
                self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    query_filter=self._document_filter(document_id),
                    limit=top_k,
                    with_payload=True,
                )
            )
        except Exception as exc:
            raise AppError(
                ErrorCode.QDRANT_UNAVAILABLE,
                "Vector search is unavailable",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def delete_document_vectors(self, document_id: str) -> None:
        """Delete all text and image points for a document."""
        try:
            from qdrant_client import models

            selector = models.FilterSelector(filter=self._document_filter(document_id))
            for collection_name in (self.settings.qdrant_text_collection, self.settings.qdrant_image_collection):
                if self.client.collection_exists(collection_name=collection_name):
                    self.client.delete(collection_name=collection_name, points_selector=selector)
        except Exception as exc:
            raise AppError(
                ErrorCode.QDRANT_UNAVAILABLE,
                "Failed to delete vectors for document",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def check_ready(self) -> dict[str, bool | str]:
        """Check Qdrant connectivity."""
        try:
            self.client.get_collections()
            return {"ready": True, "message": "Qdrant connection is healthy"}
        except Exception:
            return {"ready": False, "message": "Qdrant connection failed"}

    def _document_filter(self, document_id: str | None) -> Any | None:
        if document_id is None:
            return None
        from qdrant_client import models

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )
