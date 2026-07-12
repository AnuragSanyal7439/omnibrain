"""Search API schemas."""

from pydantic import BaseModel, Field


class TextSearchRequest(BaseModel):
    """Text search request."""

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: str | None = None


class ImageSearchRequest(BaseModel):
    """Image search request."""

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: str | None = None


class MultimodalSearchRequest(BaseModel):
    """Combined search request."""

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: str | None = None


class TextSearchResult(BaseModel):
    """Text search result."""

    score: float
    document_id: str
    document_name: str
    page_number: int
    chunk_id: str
    chunk_index: int
    text: str
    content_type: str
    citation: str
    extraction_status: str | None = None


class ImageSearchResult(BaseModel):
    """Image search result."""

    score: float
    document_id: str
    document_name: str
    page_number: int
    image_id: str
    image_index: int
    image_path: str
    width: int
    height: int
    content_type: str
    citation: str
    extraction_status: str | None = None


class TextSearchResponse(BaseModel):
    """Text search response."""

    query: str
    results: list[TextSearchResult]


class ImageSearchResponse(BaseModel):
    """Image search response."""

    query: str
    results: list[ImageSearchResult]


class MultimodalSearchResponse(BaseModel):
    """Combined multimodal response."""

    query: str
    text_results: list[TextSearchResult]
    image_results: list[ImageSearchResult]
