"""Database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())


class Document(Base):
    """Uploaded document metadata."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_text_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_images: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    ingestion_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingestion_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["IngestionEvent"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["TextChunkRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    images: Mapped[list["ExtractedImageRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class IngestionEvent(Base):
    """Stage-level ingestion event."""

    __tablename__ = "ingestion_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="events")


class DocumentPage(Base):
    """Page-level text extraction metadata."""

    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_ocr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extraction_status: Mapped[str] = mapped_column(String(50), nullable=False, default="extracted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="pages")


class TextChunkRecord(Base):
    """Chunk-level text metadata."""

    __tablename__ = "text_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    citation: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="chunks")


class ExtractedImageRecord(Base):
    """Extracted image metadata."""

    __tablename__ = "extracted_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    image_index: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="image")
    extraction_status: Mapped[str] = mapped_column(String(50), nullable=False, default="extracted")
    duplicate_of: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="images")
