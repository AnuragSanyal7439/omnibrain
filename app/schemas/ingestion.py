"""Ingestion API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestionEventRead(BaseModel):
    """Ingestion event response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    stage: str
    status: str
    message: str
    created_at: datetime
