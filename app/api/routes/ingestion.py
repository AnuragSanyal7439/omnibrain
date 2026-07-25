"""Ingestion-oriented endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.api.routes.documents import get_document_events
from app.schemas.ingestion import IngestionEventRead

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


@router.get("/{document_id}/events", response_model=list[IngestionEventRead])
async def get_ingestion_events(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> list[IngestionEventRead]:
    """Return ingestion events through an ingestion namespace alias."""
    return await get_document_events(document_id, db)
