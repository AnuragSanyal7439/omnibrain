"""Health and readiness endpoints."""

from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import check_database
from app.services.embedding_service import EmbeddingService
from app.services.image_embedding_service import ImageEmbeddingService
from app.services.vector_store_service import VectorStoreService

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return liveness information."""
    settings = get_settings()
    return {"status": "ok", "service": f"{settings.app_name} API", "version": settings.app_version}


@router.get("/ready")
async def ready() -> dict[str, Any]:
    """Return dependency readiness without leaking internal details."""
    database_ready = check_database()
    qdrant_ready = VectorStoreService().check_ready()
    text_ready = EmbeddingService().check_ready()
    image_ready = ImageEmbeddingService().check_ready()
    components = {
        "database": database_ready,
        "qdrant": qdrant_ready,
        "text_embedding_model": text_ready,
        "clip_model": image_ready,
    }
    status = "ok" if all(item["ready"] for item in components.values()) else "degraded"
    return {"status": status, "service": "OmniBrain API", "components": components}
