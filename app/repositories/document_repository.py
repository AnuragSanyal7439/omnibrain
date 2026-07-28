"""Database access for document ingestion metadata."""

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.constants import DocumentStatus, EventStatus, ProcessingStage
from app.db.models import (
    Document,
    DocumentPage,
    ExtractedImageRecord,
    IngestionEvent,
    TextChunkRecord,
)
from app.schemas.extraction import ExtractedImage, PageText, TextChunk


class DocumentRepository:
    """Repository for documents and ingestion records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_document(
        self,
        *,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_hash: str,
        mime_type: str,
        file_size: int,
        status: DocumentStatus | str,
    ) -> Document:
        """Persist a new document."""
        document = Document(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size=file_size,
            status=status.value if isinstance(status, DocumentStatus) else status,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_document(self, document_id: str) -> Document | None:
        """Return a document by ID."""
        return self.db.get(Document, document_id)

    def get_by_hash(self, file_hash: str) -> Document | None:
        """Return a document with a matching content hash."""
        return self.db.scalar(select(Document).where(Document.file_hash == file_hash))

    def list_documents(self, offset: int = 0, limit: int = 50) -> list[Document]:
        """Return documents ordered by creation date descending with pagination."""
        return list(
            self.db.scalars(
                select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
            )
        )

    def update_document(self, document: Document, **fields: object) -> Document:
        """Update fields on a document."""
        for key, value in fields.items():
            setattr(document, key, value)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def mark_processing(self, document: Document) -> Document:
        """Mark a document as processing."""
        return self.update_document(
            document,
            status=DocumentStatus.PROCESSING.value,
            error_message=None,
            ingestion_started_at=datetime.now(UTC),
        )

    def mark_completed(
        self,
        document: Document,
        *,
        status: DocumentStatus,
        total_pages: int,
        total_text_chunks: int,
        total_images: int,
        error_message: str | None = None,
    ) -> Document:
        """Mark ingestion as terminal."""
        return self.update_document(
            document,
            status=status.value,
            total_pages=total_pages,
            total_text_chunks=total_text_chunks,
            total_images=total_images,
            error_message=error_message,
            ingestion_completed_at=datetime.now(UTC),
        )

    def add_event(
        self,
        document_id: str,
        stage: ProcessingStage | str,
        event_status: EventStatus | str,
        message: str,
    ) -> IngestionEvent:
        """Add a processing event."""
        event = IngestionEvent(
            document_id=document_id,
            stage=stage.value if isinstance(stage, ProcessingStage) else stage,
            status=event_status.value if isinstance(event_status, EventStatus) else event_status,
            message=message,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(self, document_id: str) -> list[IngestionEvent]:
        """Return ingestion events for a document."""
        return list(
            self.db.scalars(
                select(IngestionEvent)
                .where(IngestionEvent.document_id == document_id)
                .order_by(IngestionEvent.created_at.asc())
            )
        )

    def replace_pages(self, document_id: str, pages: Iterable[PageText]) -> None:
        """Persist page-level extraction records."""
        self.db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        self.db.add_all([
            DocumentPage(
                document_id=document_id,
                page_number=page.page_number,
                text=page.text,
                character_count=page.character_count,
                requires_ocr=page.requires_ocr,
                extraction_status=page.extraction_status,
            )
            for page in pages
        ])
        self.db.commit()

    def replace_chunks(self, document_id: str, chunks: Iterable[TextChunk]) -> None:
        """Persist chunk-level text metadata."""
        self.db.execute(delete(TextChunkRecord).where(TextChunkRecord.document_id == document_id))
        self.db.add_all([
            TextChunkRecord(
                document_id=document_id,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                character_count=chunk.character_count,
                content_type=chunk.content_type,
                citation=chunk.citation,
            )
            for chunk in chunks
        ])
        self.db.commit()

    def replace_images(self, document_id: str, images: Iterable[ExtractedImage]) -> None:
        """Persist extracted image metadata."""
        self.db.execute(delete(ExtractedImageRecord).where(ExtractedImageRecord.document_id == document_id))
        self.db.add_all([
            ExtractedImageRecord(
                document_id=document_id,
                page_number=image.page_number,
                image_id=image.image_id,
                image_index=image.image_index,
                image_path=str(image.image_path),
                width=image.width,
                height=image.height,
                file_type=image.file_type,
                image_hash=image.image_hash,
                content_type=image.content_type,
                extraction_status=image.extraction_status,
                duplicate_of=image.duplicate_of,
            )
            for image in images
        ])
        self.db.commit()

    def delete_document(self, document: Document) -> None:
        """Delete a document and cascaded metadata."""
        self.db.delete(document)
        self.db.commit()
