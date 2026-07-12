"""FastAPI dependency providers."""

from collections.abc import Generator

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


def get_ingestion_service() -> IngestionService:
    """Create an ingestion service instance."""
    return IngestionService()


def get_search_service() -> SearchService:
    """Create a search service instance."""
    return SearchService()


def get_vector_store() -> VectorStoreService:
    """Create a vector store service instance."""
    return VectorStoreService()
