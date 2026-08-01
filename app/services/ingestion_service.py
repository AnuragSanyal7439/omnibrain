"""Background document ingestion pipeline."""

import logging
import time
from pathlib import Path

from app.core.constants import DocumentStatus, EventStatus, ProcessingStage
from app.db.session import SessionLocal
from app.repositories.document_repository import DocumentRepository
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.image_embedding_service import ImageEmbeddingService
from app.services.pdf_service import PdfService
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


class IngestionService:
    """Run the complete Week 1 ingestion pipeline for a document."""

    def __init__(
        self,
        pdf_service: PdfService | None = None,
        chunking_service: ChunkingService | None = None,
        embedding_service: EmbeddingService | None = None,
        image_embedding_service: ImageEmbeddingService | None = None,
        vector_store: VectorStoreService | None = None,
    ) -> None:
        self.pdf_service = pdf_service or PdfService()
        self.chunking_service = chunking_service or ChunkingService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.image_embedding_service = image_embedding_service or ImageEmbeddingService()
        self.vector_store = vector_store or VectorStoreService()

    def ingest_document(self, document_id: str) -> None:
        """Ingest a queued document and persist searchable vectors."""
        started = time.perf_counter()
        with SessionLocal() as db:
            repository = DocumentRepository(db)
            document = repository.get_document(document_id)
            if document is None:
                logger.warning("ingestion requested for missing document_id=%s", document_id)
                return

            repository.mark_processing(document)
            repository.add_event(document_id, ProcessingStage.PDF_PARSING, EventStatus.STARTED, "PDF parsing started")

            image_errors: list[str] = []
            try:
                pdf_path = Path(document.file_path)
                
                # Get total page count
                import fitz
                with fitz.open(pdf_path) as doc:
                    total_pages = len(doc)
                
                # Clear existing records (e.g., if this is a retry)
                repository.replace_pages(document.id, [])
                repository.replace_images(document.id, [])
                repository.replace_chunks(document.id, [])
                
                batch_size = 20
                total_extracted_pages = 0
                total_extracted_chunks = 0
                total_extracted_images = 0
                
                self.vector_store.initialize_collections()
                
                for start_page in range(1, total_pages + 1, batch_size):
                    end_page = min(start_page + batch_size - 1, total_pages)
                    
                    pages = self.pdf_service.extract_text(pdf_path, document.id, start_page=start_page, end_page=end_page)
                    repository.replace_pages(document.id, pages, clear_existing=False)
                    total_extracted_pages += len(pages)
                    
                    images, batch_image_errors = self.pdf_service.extract_images(pdf_path, document.id, start_page=start_page, end_page=end_page)
                    repository.replace_images(document.id, images, clear_existing=False)
                    image_errors.extend(batch_image_errors)
                    total_extracted_images += len(images)
                    
                    chunks = self.chunking_service.chunk_pages(pages, document.id, document.original_filename)
                    repository.replace_chunks(document.id, chunks, clear_existing=False)
                    total_extracted_chunks += len(chunks)
                    
                    text_vectors = self.embedding_service.embed_documents([chunk.text for chunk in chunks])
                    image_vectors = self.image_embedding_service.embed_images([image.image_path for image in images])
                    
                    self.vector_store.upsert_text_chunks(chunks, text_vectors)
                    self.vector_store.upsert_images(document.original_filename, images, image_vectors)
                    
                    # Clear memory explicitly
                    del pages, images, chunks, text_vectors, image_vectors

                repository.add_event(
                    document_id,
                    ProcessingStage.TEXT_EXTRACTION,
                    EventStatus.SUCCEEDED,
                    f"Extracted text from {total_extracted_pages} pages",
                )
                image_status = EventStatus.WARNING if image_errors else EventStatus.SUCCEEDED
                repository.add_event(
                    document_id,
                    ProcessingStage.IMAGE_EXTRACTION,
                    image_status,
                    f"Extracted {total_extracted_images} images",
                )
                repository.add_event(
                    document_id,
                    ProcessingStage.TEXT_CHUNKING,
                    EventStatus.SUCCEEDED,
                    f"Created {total_extracted_chunks} text chunks",
                )
                repository.add_event(
                    document_id,
                    ProcessingStage.QDRANT_STORAGE,
                    EventStatus.SUCCEEDED,
                    "Inserted vectors into Qdrant",
                )

                terminal_status = DocumentStatus.PARTIALLY_COMPLETED if image_errors else DocumentStatus.COMPLETED
                error_message = "; ".join(image_errors[:3]) if image_errors else None
                repository.mark_completed(
                    document,
                    status=terminal_status,
                    total_pages=total_extracted_pages,
                    total_text_chunks=total_extracted_chunks,
                    total_images=total_extracted_images,
                    error_message=error_message,
                )
                repository.add_event(
                    document_id,
                    ProcessingStage.COMPLETED,
                    EventStatus.SUCCEEDED,
                    f"Ingestion completed in {round(time.perf_counter() - started, 2)} seconds",
                )
                logger.info(
                    "ingestion completed document_id=%s pages=%s chunks=%s images=%s",
                    document_id,
                    total_extracted_pages,
                    total_extracted_chunks,
                    total_extracted_images,
                )
            except Exception as exc:
                message = str(exc)[:1000]
                repository.mark_completed(
                    document,
                    status=DocumentStatus.FAILED,
                    total_pages=document.total_pages,
                    total_text_chunks=document.total_text_chunks,
                    total_images=document.total_images,
                    error_message=message,
                )
                repository.add_event(
                    document_id,
                    ProcessingStage.COMPLETED,
                    EventStatus.FAILED,
                    "Ingestion failed",
                )
                logger.exception("ingestion failed document_id=%s", document_id)
