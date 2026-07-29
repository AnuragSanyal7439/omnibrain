"""Health and readiness endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_search_service, get_vector_store
from app.core.config import get_settings
from app.db.session import check_database
from app.services.search_service import SearchService
from app.services.vector_store_service import VectorStoreService

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return liveness information."""
    settings = get_settings()
    return {"status": "ok", "service": f"{settings.app_name} API", "version": settings.app_version}


@router.get("/ready")
async def ready(
    vector_store: Annotated[VectorStoreService, Depends(get_vector_store)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> dict[str, Any]:
    """Return dependency readiness without leaking internal details."""
    database_ready = check_database()
    qdrant_ready = vector_store.check_ready()
    text_ready = search_service.embedding_service.check_ready()
    image_ready = search_service.image_embedding_service.check_ready()
    components = {
        "database": database_ready,
        "qdrant": qdrant_ready,
        "text_embedding_model": text_ready,
        "clip_model": image_ready,
    }
    status = "ok" if all(item["ready"] for item in components.values()) else "degraded"
    return {"status": status, "service": "OmniBrain API", "components": components}
