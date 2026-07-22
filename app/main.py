"""FastAPI application entry point."""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, health, ingestion, search
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, log_extra, request_id_context
from app.db.session import init_db
from app.utils.file_utils import ensure_storage_dirs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown logic for the application."""
    ensure_storage_dirs()
    init_db()
    try:
        from app.services.vector_store_service import VectorStoreService

        VectorStoreService().initialize_collections()
    except Exception:
        logger.warning("Qdrant collection initialization skipped")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.app_log_level)

    app = FastAPI(
        title=f"{settings.app_name} API",
        description="Week 1 multimodal document-ingestion backend.",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    register_exception_handlers(app)

    @app.middleware("http")
    async def body_size_limiter(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Reject requests that declare a Content-Length exceeding the upload limit."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_upload_size_bytes:
            return Response(content="Request body too large", status_code=413)
        return await call_next(request)

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        token = request_id_context.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request completed %s",
                log_extra(method=request.method, path=request.url.path, duration_ms=elapsed_ms),
            )
            request_id_context.reset(token)
        return response

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Return friendly API entrypoint links."""
        return {
            "service": f"{settings.app_name} API",
            "status": "ok",
            "docs": "/docs",
            "health": "/health",
            "ready": "/ready",
        }

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(ingestion.router)
    app.include_router(search.router)
    return app


app = create_app()
