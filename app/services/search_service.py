"""Search orchestration service."""

from app.schemas.search import (
    ImageSearchRequest,
    ImageSearchResponse,
    MultimodalSearchRequest,
    MultimodalSearchResponse,
    TextSearchRequest,
    TextSearchResponse,
)
from app.services.embedding_service import EmbeddingService
from app.services.image_embedding_service import ImageEmbeddingService
from app.services.vector_store_service import VectorStoreService


class SearchService:
    """Run semantic searches against Qdrant collections."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        image_embedding_service: ImageEmbeddingService | None = None,
        vector_store: VectorStoreService | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.image_embedding_service = image_embedding_service or ImageEmbeddingService()
        self.vector_store = vector_store or VectorStoreService()

    def search_text(self, request: TextSearchRequest) -> TextSearchResponse:
        """Search text chunks in the text embedding space."""
        vector = self.embedding_service.embed_query(request.query)
        results = self.vector_store.search_text(vector, request.top_k, request.document_id)
        return TextSearchResponse(query=request.query, results=results)

    def search_images(self, request: ImageSearchRequest) -> ImageSearchResponse:
        """Search images in the CLIP semantic space."""
        vector = self.image_embedding_service.embed_text_query(request.query)
        results = self.vector_store.search_images(vector, request.top_k, request.document_id)
        return ImageSearchResponse(query=request.query, results=results)

    def search_multimodal(self, request: MultimodalSearchRequest) -> MultimodalSearchResponse:
        """Run text and image search independently without score fusion."""
        text_results = self.search_text(
            TextSearchRequest(query=request.query, top_k=request.top_k, document_id=request.document_id)
        ).results
        image_results = self.search_images(
            ImageSearchRequest(query=request.query, top_k=request.top_k, document_id=request.document_id)
        ).results
        return MultimodalSearchResponse(query=request.query, text_results=text_results, image_results=image_results)
