"""Recursive text chunking service."""

import re
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.constants import TEXT_CONTENT_TYPE
from app.services.pdf_service import PageText
from app.utils.ids import stable_uuid


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


class ChunkingService:
    """Split extracted PDF text into overlapping page-scoped chunks."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        min_chunk_chars: int | None = None,
    ) -> None:
        settings = get_settings()
        self.chunk_size = chunk_size or settings.text_chunk_size
        self.chunk_overlap = chunk_overlap or settings.text_chunk_overlap
        self.min_chunk_chars = min_chunk_chars or settings.min_text_chunk_chars
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")

    def chunk_pages(self, pages: list[PageText], document_id: str, document_name: str) -> list[TextChunk]:
        """Chunk each PDF page independently."""
        chunks: list[TextChunk] = []
        chunk_index = 0
        for page in pages:
            if not page.text.strip():
                continue
            page_chunks = self._split_text(page.text)
            for text in page_chunks:
                if len(text.strip()) < self.min_chunk_chars:
                    continue
                chunk_id = stable_uuid(f"text:{document_id}:{page.page_number}:{chunk_index}:{text[:64]}")
                chunks.append(
                    TextChunk(
                        document_id=document_id,
                        document_name=document_name,
                        page_number=page.page_number,
                        chunk_id=chunk_id,
                        chunk_index=chunk_index,
                        text=text,
                        character_count=len(text),
                        content_type=TEXT_CONTENT_TYPE,
                        citation=f"{document_name}, page {page.page_number}",
                    )
                )
                chunk_index += 1
        return chunks

    def _split_text(self, text: str) -> list[str]:
        normalized = text.strip()
        if len(normalized) <= self.chunk_size:
            return [normalized] if normalized else []

        units = self._recursive_units(normalized)
        chunks: list[str] = []
        current = ""
        for unit in units:
            candidate = f"{current} {unit}".strip() if current else unit.strip()
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current.strip())
                current = self._with_overlap(current, unit)
            else:
                chunks.extend(self._hard_split(unit))
                current = ""
        if current.strip():
            chunks.append(current.strip())
        return self._merge_tiny_tail(chunks)

    def _recursive_units(self, text: str) -> list[str]:
        for pattern in (r"\n\s*\n+", r"(?<=[.!?])\s+", r"\s+"):
            units = [part.strip() for part in re.split(pattern, text) if part.strip()]
            if units and max(len(part) for part in units) <= self.chunk_size:
                return units
        return self._hard_split(text)

    def _hard_split(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end].strip())
            if end == len(text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return [chunk for chunk in chunks if chunk]

    def _with_overlap(self, previous: str, next_unit: str) -> str:
        overlap_text = previous[-self.chunk_overlap :].strip()
        candidate = f"{overlap_text} {next_unit}".strip()
        if len(candidate) <= self.chunk_size:
            return candidate
        return next_unit.strip()

    def _merge_tiny_tail(self, chunks: list[str]) -> list[str]:
        if len(chunks) < 2 or len(chunks[-1]) >= self.min_chunk_chars:
            return chunks
        merged = f"{chunks[-2]} {chunks[-1]}".strip()
        if len(merged) <= self.chunk_size + self.chunk_overlap:
            return [*chunks[:-2], merged]
        return chunks
