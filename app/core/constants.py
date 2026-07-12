"""Application constants."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Supported document lifecycle statuses."""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


class ProcessingStage(StrEnum):
    """Known ingestion stages."""

    FILE_VALIDATION = "file_validation"
    PDF_PARSING = "pdf_parsing"
    TEXT_EXTRACTION = "text_extraction"
    IMAGE_EXTRACTION = "image_extraction"
    TEXT_CHUNKING = "text_chunking"
    TEXT_EMBEDDING = "text_embedding"
    IMAGE_EMBEDDING = "image_embedding"
    QDRANT_STORAGE = "qdrant_storage"
    COMPLETED = "completed"


class EventStatus(StrEnum):
    """Processing event statuses."""

    STARTED = "started"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    WARNING = "warning"
    FAILED = "failed"


TEXT_CONTENT_TYPE = "text"
IMAGE_CONTENT_TYPE = "image"
PDF_MAGIC_BYTES = b"%PDF"
