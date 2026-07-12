"""Document API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadDocumentResponse(BaseModel):
    """Upload acceptance response."""

    document_id: str
    filename: str
    status: str
    message: str


class DocumentListItem(BaseModel):
    """Document list item."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: str
    total_pages: int
    total_text_chunks: int
    total_images: int
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentListItem):
    """Detailed document metadata."""

    stored_filename: str
    file_hash: str
    mime_type: str
    file_size: int
    file_path: str
    error_message: str | None
    ingestion_started_at: datetime | None
    ingestion_completed_at: datetime | None


class DocumentStatusResponse(BaseModel):
    """Document status response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: str
    total_pages: int
    total_text_chunks: int
    total_images: int
    error_message: str | None
    ingestion_started_at: datetime | None
    ingestion_completed_at: datetime | None


class DeleteDocumentResponse(BaseModel):
    """Document deletion response."""

    document_id: str
    deleted: bool
    message: str
