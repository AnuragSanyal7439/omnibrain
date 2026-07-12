"""Text embedding provider abstraction."""

import logging
from importlib.util import find_spec
from typing import Any, Protocol

from fastapi import status

from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode

logger = logging.getLogger(__name__)


class TextEmbeddingProvider(Protocol):
    """Text embedding provider interface."""

    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query."""
        ...

    def check_ready(self) -> dict[str, bool | str]:
        """Return provider readiness."""
        ...


class LocalSentenceTransformerProvider:
    """Local sentence-transformers embedding provider."""

    def __init__(self, model_name: str, batch_size: int, expected_dimension: int) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.dimension = expected_dimension
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                model_dimension = self._model.get_sentence_embedding_dimension()
                if model_dimension is None:
                    raise AppError(
                        ErrorCode.EMBEDDING_FAILURE,
                        "Text embedding model did not report a vector dimension",
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                actual_dimension = int(model_dimension)
                if actual_dimension != self.dimension:
                    raise AppError(
                        ErrorCode.EMBEDDING_FAILURE,
                        f"Text embedding dimension mismatch: expected {self.dimension}, got {actual_dimension}",
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            except AppError:
                raise
            except Exception as exc:
                raise AppError(
                    ErrorCode.EMBEDDING_FAILURE,
                    "Failed to load local text embedding model",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents in batches."""
        if not texts:
            return []
        model = self._load_model()
        vectors = model.encode(  # type: ignore[attr-defined]
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vector.astype(float).tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        return self.embed_documents([text])[0]

    def check_ready(self) -> dict[str, bool | str]:
        """Check whether local embedding dependencies are importable.

        Model weights are loaded lazily during ingestion/search so readiness does
        not trigger large downloads or expensive imports.
        """
        if find_spec("sentence_transformers") is None:
            return {"ready": False, "message": "sentence-transformers is not installed"}
        return {"ready": True, "message": "Local text embedding provider is configured"}


class OpenAIEmbeddingProvider:
    """Optional OpenAI embedding provider."""

    def __init__(self, model_name: str, batch_size: int, api_key: str | None, expected_dimension: int) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.api_key = api_key
        self.dimension = expected_dimension
        self._client: Any | None = None

    def _load_client(self) -> Any:
        if not self.api_key:
            raise AppError(
                ErrorCode.EMBEDDING_FAILURE,
                "OPENAI_API_KEY is required for OpenAI embeddings",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            except Exception as exc:
                raise AppError(
                    ErrorCode.EMBEDDING_FAILURE,
                    "Failed to initialize OpenAI embedding client",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents with OpenAI in batches."""
        if not texts:
            return []
        client = self._load_client()
        results: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = client.embeddings.create(model=self.model_name, input=batch)  # type: ignore[attr-defined]
            for item in response.data:
                vector = list(item.embedding)
                if len(vector) != self.dimension:
                    raise AppError(
                        ErrorCode.EMBEDDING_FAILURE,
                        f"Text embedding dimension mismatch: expected {self.dimension}, got {len(vector)}",
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                results.append(vector)
        return results

    def embed_query(self, text: str) -> list[float]:
        """Embed a query with OpenAI."""
        return self.embed_documents([text])[0]

    def check_ready(self) -> dict[str, bool | str]:
        """Check client configuration without making a paid API call."""
        if self.api_key:
            return {"ready": True, "message": "OpenAI embedding provider is configured"}
        return {"ready": False, "message": "OpenAI embedding provider is missing an API key"}


class EmbeddingService:
    """Facade for text embedding providers."""

    def __init__(self, provider: TextEmbeddingProvider | None = None) -> None:
        settings = get_settings()
        if provider is not None:
            self.provider = provider
        elif settings.text_embedding_provider.lower() == "openai":
            self.provider = OpenAIEmbeddingProvider(
                settings.text_embedding_model,
                settings.text_embedding_batch_size,
                settings.openai_api_key,
                settings.text_embedding_dimension,
            )
        else:
            self.provider = LocalSentenceTransformerProvider(
                settings.text_embedding_model,
                settings.text_embedding_batch_size,
                settings.text_embedding_dimension,
            )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed text chunks."""
        vectors = self.provider.embed_documents(texts)
        self._validate_dimensions(vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query."""
        vector = self.provider.embed_query(text)
        self._validate_dimensions([vector])
        return vector

    def check_ready(self) -> dict[str, bool | str]:
        """Return provider readiness."""
        return self.provider.check_ready()

    def _validate_dimensions(self, vectors: list[list[float]]) -> None:
        for vector in vectors:
            if len(vector) != self.provider.dimension:
                raise AppError(
                    ErrorCode.EMBEDDING_FAILURE,
                    f"Text embedding dimension mismatch: expected {self.provider.dimension}, got {len(vector)}",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
