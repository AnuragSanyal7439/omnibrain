"""Document upload and management tests."""

from app.db.session import SessionLocal
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService


def test_invalid_file_type_rejected(client) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_valid_pdf_upload_returns_accepted(client, pdf_file) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", pdf_file.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["document_id"]


def test_duplicate_pdf_detection(client, pdf_file) -> None:
    payload = pdf_file.read_bytes()
    first = client.post("/api/v1/documents/upload", files={"file": ("sample.pdf", payload, "application/pdf")})
    assert first.status_code == 202
    second = client.post("/api/v1/documents/upload", files={"file": ("copy.pdf", payload, "application/pdf")})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_DOCUMENT"


def test_status_endpoint(client, pdf_file) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", pdf_file.read_bytes(), "application/pdf")},
    )
    document_id = response.json()["document_id"]
    status_response = client.get(f"/api/v1/documents/{document_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "queued"


def test_document_deletion(client, pdf_file) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", pdf_file.read_bytes(), "application/pdf")},
    )
    document_id = response.json()["document_id"]
    delete_response = client.delete(f"/api/v1/documents/{document_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404


def test_file_size_validation(client) -> None:
    payload = b"%PDF" + (b"x" * (2 * 1024 * 1024))
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("large.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_failed_ingestion_status(pdf_file) -> None:
    class BrokenPdfService:
        def extract_text(self, *_args):
            raise RuntimeError("corrupted")

    with SessionLocal() as db:
        service = DocumentService(db)
        document = service.repository.create_document(
            original_filename="bad.pdf",
            stored_filename="bad.pdf",
            file_path=str(pdf_file),
            file_hash="hash",
            mime_type="application/pdf",
            file_size=pdf_file.stat().st_size,
            status="queued",
        )

    from app.services.ingestion_service import IngestionService

    IngestionService(pdf_service=BrokenPdfService()).ingest_document(document.id)

    with SessionLocal() as db:
        stored = DocumentRepository(db).get_document(document.id)
        assert stored is not None
        assert stored.status == "failed"
