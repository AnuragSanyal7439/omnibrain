"""Structured application exceptions and handlers."""

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class ErrorCode(StrEnum):
    """Machine-readable error codes."""

    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    INVALID_PDF = "INVALID_PDF"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    QDRANT_UNAVAILABLE = "QDRANT_UNAVAILABLE"
    EMBEDDING_FAILURE = "EMBEDDING_FAILURE"
    IMAGE_EXTRACTION_FAILURE = "IMAGE_EXTRACTION_FAILURE"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class AppError(Exception):
    """Base application exception converted to structured JSON."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    """Build a standardized error response body."""
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers on a FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code.value, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload(ErrorCode.VALIDATION_ERROR.value, "Request validation failed", exc.errors()),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload(ErrorCode.DATABASE_FAILURE.value, "Database operation failed"),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload(ErrorCode.UNEXPECTED_ERROR.value, "Unexpected server error"),
        )
