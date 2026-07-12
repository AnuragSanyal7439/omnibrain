"""Pytest fixtures for OmniBrain."""

import os
import sys
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATA = PROJECT_ROOT / "data" / "test_runtime"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATA / 'test_omnibrain.db'}"
os.environ["UPLOAD_DIR"] = str(TEST_DATA / "uploads")
os.environ["EXTRACTED_IMAGES_DIR"] = str(TEST_DATA / "extracted_images")
os.environ["SAMPLE_DOCUMENTS_DIR"] = str(TEST_DATA / "sample_documents")
os.environ["MAX_UPLOAD_SIZE_MB"] = "1"
os.environ["TEXT_CHUNK_SIZE"] = "200"
os.environ["TEXT_CHUNK_OVERLAP"] = "40"
os.environ["MIN_IMAGE_WIDTH"] = "50"
os.environ["MIN_IMAGE_HEIGHT"] = "50"

from app.api.dependencies import get_ingestion_service, get_search_service, get_vector_store  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.repositories.document_repository import DocumentRepository  # noqa: E402
from app.schemas.search import (  # noqa: E402
    ImageSearchResponse,
    ImageSearchResult,
    TextSearchResponse,
    TextSearchResult,
)


class FakeIngestionService:
    """No-op ingestion service for upload endpoint tests."""

    def ingest_document(self, document_id: str) -> None:
        with next_db_session() as db:
            repository = DocumentRepository(db)
            document = repository.get_document(document_id)
            if document is not None:
                repository.update_document(document, status="queued")


class FakeVectorStore:
    """Vector store double used by API deletion tests."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_document_vectors(self, document_id: str) -> None:
        self.deleted.append(document_id)


class FakeSearchService:
    """Search service double with schema-faithful results."""

    def search_text(self, request: Any) -> TextSearchResponse:
        return TextSearchResponse(
            query=request.query,
            results=[
                TextSearchResult(
                    score=0.9,
                    document_id="doc-1",
                    document_name="sample.pdf",
                    page_number=1,
                    chunk_id="chunk-1",
                    chunk_index=0,
                    text="Revenue increased because subscriptions grew.",
                    content_type="text",
                    citation="sample.pdf, page 1",
                    extraction_status="extracted",
                )
            ],
        )

    def search_images(self, request: Any) -> ImageSearchResponse:
        return ImageSearchResponse(
            query=request.query,
            results=[
                ImageSearchResult(
                    score=0.8,
                    document_id="doc-1",
                    document_name="sample.pdf",
                    page_number=2,
                    image_id="image-1",
                    image_index=1,
                    image_path="data/test_runtime/image.png",
                    width=640,
                    height=360,
                    content_type="image",
                    citation="sample.pdf, page 2, image 1",
                    extraction_status="extracted",
                )
            ],
        )

    def search_multimodal(self, request: Any) -> Any:
        return {
            "query": request.query,
            "text_results": self.search_text(request).results,
            "image_results": self.search_images(request).results,
        }


def next_db_session() -> Any:
    from app.db.session import SessionLocal

    return SessionLocal()


@pytest.fixture(autouse=True)
def reset_database() -> None:
    get_settings.cache_clear()
    for directory in (TEST_DATA / "uploads", TEST_DATA / "extracted_images", TEST_DATA / "sample_documents"):
        directory.mkdir(parents=True, exist_ok=True)
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_ingestion_service] = lambda: FakeIngestionService()
    app.dependency_overrides[get_vector_store] = lambda: FakeVectorStore()
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Revenue grew in Q1. Customer retention improved.\n\nSubscriptions were the main driver.",
        fontsize=12,
    )
    document.save(path)
    document.close()
    return path


@pytest.fixture
def pdf_with_image(tmp_path: Path) -> Path:
    image_path = tmp_path / "chart.png"
    image = Image.new("RGB", (200, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 40, 60, 110], fill=(20, 100, 180))
    draw.rectangle([80, 20, 120, 110], fill=(20, 100, 180))
    image.save(image_path)

    path = tmp_path / "with_image.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "This page contains a revenue chart.", fontsize=12)
    page.insert_image(fitz.Rect(72, 120, 272, 240), filename=str(image_path))
    document.save(path)
    document.close()
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "empty.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    return path
