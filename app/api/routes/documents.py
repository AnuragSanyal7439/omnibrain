"""Document management endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_ingestion_service, get_vector_store
from app.core.exceptions import AppError, ErrorCode
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentListItem,
    DocumentStatusResponse,
    UploadDocumentResponse,
)
from app.schemas.ingestion import IngestionEventRead
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.vector_store_service import VectorStoreService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=UploadDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF document")],
    db: Annotated[Session, Depends(get_db_session)],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    vector_store: Annotated[VectorStoreService, Depends(get_vector_store)],
) -> UploadDocumentResponse:
    """Accept a PDF upload and enqueue asynchronous ingestion."""
    service = DocumentService(db, vector_store)
    response = await service.upload_pdf(file)
    background_tasks.add_task(ingestion_service.ingest_document, response.document_id)
    return response


@router.get("", response_model=list[DocumentListItem])
async def list_documents(
    db: Annotated[Session, Depends(get_db_session)],
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of documents to return")] = 50,
) -> list[DocumentListItem]:
    """List uploaded documents with optional pagination."""
    return [
        DocumentListItem.model_validate(item)
        for item in DocumentRepository(db).list_documents(offset=offset, limit=limit)
    ]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> DocumentDetail:
    """Return document metadata."""
    document = DocumentRepository(db).get_document(document_id)
    if document is None:
        raise AppError(ErrorCode.DOCUMENT_NOT_FOUND, "Document was not found", status.HTTP_404_NOT_FOUND)
    return DocumentDetail.model_validate(document)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> DocumentStatusResponse:
    """Return the current ingestion status for a document."""
    document = DocumentRepository(db).get_document(document_id)
    if document is None:
        raise AppError(ErrorCode.DOCUMENT_NOT_FOUND, "Document was not found", status.HTTP_404_NOT_FOUND)
    return DocumentStatusResponse.model_validate(document)


@router.get("/{document_id}/events", response_model=list[IngestionEventRead])
async def get_document_events(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> list[IngestionEventRead]:
    """Return processing events for a document."""
    repository = DocumentRepository(db)
    if repository.get_document(document_id) is None:
        raise AppError(ErrorCode.DOCUMENT_NOT_FOUND, "Document was not found", status.HTTP_404_NOT_FOUND)
    return [IngestionEventRead.model_validate(event) for event in repository.list_events(document_id)]


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    vector_store: Annotated[VectorStoreService, Depends(get_vector_store)],
) -> DeleteDocumentResponse:
    """Delete document metadata, files, extracted assets, and vectors."""
    service = DocumentService(db, vector_store)
    try:
        return service.delete_document(document_id)
    except AppError:
        raise
    except Exception as exc:  # pragma: no cover - defensive conversion
        raise HTTPException(status_code=500, detail=str(exc)) from exc
