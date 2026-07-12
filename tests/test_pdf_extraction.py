"""PDF extraction tests."""

from app.services.pdf_service import PdfService


def test_pdf_text_extraction(pdf_file) -> None:
    pages = PdfService().extract_text(pdf_file, "doc-1")
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "Revenue grew" in pages[0].text
    assert pages[0].requires_ocr is False


def test_image_metadata_extraction(pdf_with_image) -> None:
    images, errors = PdfService().extract_images(pdf_with_image, "doc-1")
    assert errors == []
    assert len(images) == 1
    assert images[0].page_number == 1
    assert images[0].width >= 50
    assert images[0].content_type == "image"
    assert images[0].image_path.exists()


def test_empty_page_requires_ocr(empty_pdf) -> None:
    pages = PdfService().extract_text(empty_pdf, "doc-1")
    assert len(pages) == 1
    assert pages[0].text == ""
    assert pages[0].requires_ocr is True
    assert pages[0].extraction_status == "requires_ocr"
