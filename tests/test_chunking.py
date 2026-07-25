"""Chunking service tests."""

from app.services.chunking_service import ChunkingService
from app.schemas.extraction import PageText


def test_chunking_creates_overlapping_page_scoped_chunks() -> None:
    text = "Sentence one about revenue growth. " * 20
    page = PageText(
        document_id="doc-1",
        page_number=1,
        text=text,
        character_count=len(text),
        requires_ocr=False,
        extraction_status="extracted",
    )
    chunks = ChunkingService(chunk_size=120, chunk_overlap=30, min_chunk_chars=20).chunk_pages(
        [page],
        "doc-1",
        "report.pdf",
    )
    assert len(chunks) > 1
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.content_type == "text" for chunk in chunks)
    assert all(chunk.character_count >= 20 for chunk in chunks)
