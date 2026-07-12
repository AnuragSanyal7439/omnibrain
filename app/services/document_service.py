"""Document upload, validation, and deletion service."""

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import PDF_MAGIC_BYTES, DocumentStatus, EventStatus, ProcessingStage
from app.core.exceptions import AppError, ErrorCode
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DeleteDocumentResponse, UploadDocumentResponse
from app.services.vector_store_service import VectorStoreService
from app.utils.file_utils import ensure_storage_dirs, remove_path_safely, sanitize_filename
from app.utils.hashing import sha256_bytes

logger = logging.getLogger(__name__)


class DocumentService:
    """Handle upload validation, storage, metadata, and deletion."""

    def __init__(self, db: Session, vector_store: VectorStoreService | None = None) -> None:
        self.db = db
        self.repository = DocumentRepository(db)
        self.settings = get_settings()
        self.vector_store = vector_store or VectorStoreService()

    async def upload_pdf(self, file: UploadFile) -> UploadDocumentResponse:
        """Validate and persist an uploaded PDF without running ingestion inline."""
        ensure_storage_dirs()
        original_filename = sanitize_filename(file.filename or "document.pdf")
        content_type = file.content_type or "application/octet-stream"
        if content_type not in {"application/pdf", "application/x-pdf"}:
            raise AppError(
                ErrorCode.INVALID_FILE_TYPE, "Only PDF files are supported", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            )

        payload = await file.read()
        if len(payload) > self.settings.max_upload_size_bytes:
            raise AppError(
                ErrorCode.FILE_TOO_LARGE,
                f"PDF exceeds maximum upload size of {self.settings.max_upload_size_mb} MB",
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        if not payload.startswith(PDF_MAGIC_BYTES):
            raise AppError(ErrorCode.INVALID_PDF, "Uploaded file is not a valid PDF", status.HTTP_400_BAD_REQUEST)

        file_hash = sha256_bytes(payload)
        duplicate = self.repository.get_by_hash(file_hash)
        if duplicate is not None:
            raise AppError(
                ErrorCode.DUPLICATE_DOCUMENT,
                "A document with the same content has already been uploaded",
                status.HTTP_409_CONFLICT,
                {"document_id": duplicate.id},
            )

        stored_filename = f"{uuid4()}.pdf"
        destination = self.settings.upload_dir / stored_filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

        document = self.repository.create_document(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(destination),
            file_hash=file_hash,
            mime_type=content_type,
            file_size=len(payload),
            status=DocumentStatus.QUEUED,
        )
        self.repository.add_event(
            document.id,
            ProcessingStage.FILE_VALIDATION,
            EventStatus.SUCCEEDED,
            "Document accepted and queued for ingestion",
        )
        logger.info("document queued document_id=%s filename=%s", document.id, original_filename)
        return UploadDocumentResponse(
            document_id=document.id,
            filename=original_filename,
            status=DocumentStatus.QUEUED.value,
            message="Document accepted for ingestion",
        )

    def delete_document(self, document_id: str) -> DeleteDocumentResponse:
        """Delete a document, extracted files, database rows, and Qdrant vectors."""
        document = self.repository.get_document(document_id)
        if document is None:
            raise AppError(ErrorCode.DOCUMENT_NOT_FOUND, "Document was not found", status.HTTP_404_NOT_FOUND)

        self.vector_store.delete_document_vectors(document_id)
        upload_path = Path(document.file_path)
        image_paths = [Path(image.image_path) for image in document.images]
        self.repository.delete_document(document)

        remove_path_safely(upload_path, [self.settings.upload_dir])
        for image_path in image_paths:
            remove_path_safely(image_path, [self.settings.extracted_images_dir])

        return DeleteDocumentResponse(
            document_id=document_id,
            deleted=True,
            message="Document and associated artifacts deleted",
        )
