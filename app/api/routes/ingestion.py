"""Ingestion-oriented endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.core.exceptions import AppError, ErrorCode
from app.repositories.document_repository import DocumentRepository
from app.schemas.ingestion import IngestionEventRead

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


@router.get("/{document_id}/events", response_model=list[IngestionEventRead])
async def get_ingestion_events(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> list[IngestionEventRead]:
    """Return ingestion events through an ingestion namespace alias."""
    repository = DocumentRepository(db)
    if repository.get_document(document_id) is None:
        raise AppError(ErrorCode.DOCUMENT_NOT_FOUND, "Document was not found", status.HTTP_404_NOT_FOUND)
    return [IngestionEventRead.model_validate(event) for event in repository.list_events(document_id)]
