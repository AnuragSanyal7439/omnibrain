"""Intermediate extraction and chunking data structures."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageText:
    """Extracted text for a single 1-based PDF page."""

    document_id: str
    page_number: int
    text: str
    character_count: int
    requires_ocr: bool
    extraction_status: str


@dataclass(frozen=True)
class ExtractedImage:
    """Metadata for an extracted raster image."""

    document_id: str
    page_number: int
    image_id: str
    image_index: int
    image_path: Path
    width: int
    height: int
    file_type: str
    image_hash: str
    content_type: str
    extraction_status: str
    duplicate_of: str | None = None


@dataclass(frozen=True)
class TextChunk:
    """A page-scoped text chunk."""

    document_id: str
    document_name: str
    page_number: int
    chunk_id: str
    chunk_index: int
    text: str
    character_count: int
    content_type: str
    citation: str
