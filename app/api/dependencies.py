"""FastAPI dependency providers."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService
from app.services.vector_store_service import VectorStoreService


def get_app_settings() -> Settings:
    """Return cached application settings."""
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session for request handlers."""
    yield from get_db()


@lru_cache
def get_ingestion_service() -> IngestionService:
    """Return a cached ingestion service instance.

    Cached so that the underlying embedding models (Sentence Transformers,
    CLIP) are loaded once and reused across requests.
    """
    return IngestionService()


@lru_cache
def get_search_service() -> SearchService:
    """Return a cached search service instance.

    Cached so that the underlying embedding models are loaded once and
    reused across requests.
    """
    return SearchService()


@lru_cache
def get_vector_store() -> VectorStoreService:
    """Return a cached vector store service instance."""
    return VectorStoreService()
