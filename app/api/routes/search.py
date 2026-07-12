"""Search endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_search_service
from app.schemas.search import (
    ImageSearchRequest,
    ImageSearchResponse,
    MultimodalSearchRequest,
    MultimodalSearchResponse,
    TextSearchRequest,
    TextSearchResponse,
)
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("/text", response_model=TextSearchResponse)
async def text_search(
    request: TextSearchRequest,
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> TextSearchResponse:
    """Search text chunks by semantic similarity."""
    return search_service.search_text(request)


@router.post("/images", response_model=ImageSearchResponse)
async def image_search(
    request: ImageSearchRequest,
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> ImageSearchResponse:
    """Search extracted images with a natural-language CLIP query."""
    return search_service.search_images(request)


@router.post("/multimodal", response_model=MultimodalSearchResponse)
async def multimodal_search(
    request: MultimodalSearchRequest,
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> MultimodalSearchResponse:
    """Run text and image search independently without score fusion."""
    return search_service.search_multimodal(request)
