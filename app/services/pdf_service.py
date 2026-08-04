"""PDF text and embedded image extraction service."""

import io
import re
from pathlib import Path

import fitz
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.constants import IMAGE_CONTENT_TYPE
from app.core.exceptions import AppError, ErrorCode
from app.schemas.extraction import ExtractedImage, PageText
from app.utils.hashing import sha256_bytes
from app.utils.ids import stable_uuid


class PdfService:
    """Extract text and embedded images from PDF documents."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_page_count(self, pdf_path: Path) -> int:
        """Return the total number of pages in a PDF document."""
        try:
            with fitz.open(pdf_path) as document:
                return len(document)
        except Exception as exc:
            raise AppError(ErrorCode.INVALID_PDF, "PDF could not be opened") from exc

    def extract_text(self, pdf_path: Path, document_id: str, start_page: int | None = None, end_page: int | None = None) -> list[PageText]:
        """Extract normalized text records from PDF pages within the specified range."""
        try:
            with fitz.open(pdf_path) as document:
                return self._extract_text_from_doc(document, document_id, start_page, end_page)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorCode.INVALID_PDF, "PDF could not be parsed") from exc

    def extract_images(self, pdf_path: Path, document_id: str, start_page: int | None = None, end_page: int | None = None) -> tuple[list[ExtractedImage], list[str]]:
        """Extract embedded raster images while keeping page-level metadata within the specified range."""
        try:
            with fitz.open(pdf_path) as document:
                return self._extract_images_from_doc(document, document_id, start_page, end_page)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorCode.INVALID_PDF, "PDF images could not be inspected") from exc

    def extract_page_range(
        self,
        pdf_path: Path,
        document_id: str,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> tuple[list[PageText], list[ExtractedImage], list[str]]:
        """Extract text and images from a page range in a single PDF open.

        This avoids opening the same PDF file twice per batch during ingestion.
        """
        try:
            with fitz.open(pdf_path) as document:
                pages = self._extract_text_from_doc(document, document_id, start_page, end_page)
                images, errors = self._extract_images_from_doc(document, document_id, start_page, end_page)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(ErrorCode.INVALID_PDF, "PDF could not be parsed") from exc
        return pages, images, errors

    def _extract_text_from_doc(
        self, document: fitz.Document, document_id: str, start_page: int | None = None, end_page: int | None = None,
    ) -> list[PageText]:
        """Extract text from an already-opened fitz document."""
        pages: list[PageText] = []
        total_pages = len(document)
        start = max(1, start_page) if start_page is not None else 1
        end = min(total_pages, end_page) if end_page is not None else total_pages

        for index in range(start, end + 1):
            page = document[index - 1]
            raw_text = page.get_text("text")
            text = self._normalize_text(raw_text)
            pages.append(
                PageText(
                    document_id=document_id,
                    page_number=index,
                    text=text,
                    character_count=len(text),
                    requires_ocr=not bool(text.strip()),
                    extraction_status="requires_ocr" if not text.strip() else "extracted",
                )
            )
        return pages

    def _extract_images_from_doc(
        self, document: fitz.Document, document_id: str, start_page: int | None = None, end_page: int | None = None,
    ) -> tuple[list[ExtractedImage], list[str]]:
        """Extract images from an already-opened fitz document."""
        output_dir = self.settings.extracted_images_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        images: list[ExtractedImage] = []
        errors: list[str] = []
        seen_hashes: dict[str, str] = {}
        total_pages = len(document)
        start = max(1, start_page) if start_page is not None else 1
        end = min(total_pages, end_page) if end_page is not None else total_pages

        for page_index in range(start, end + 1):
            page = document[page_index - 1]
            for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                try:
                    xref = image_info[0]
                    extracted = document.extract_image(xref)
                    image_bytes = extracted["image"]
                    converted, width, height = self._to_png(image_bytes)
                    if width < self.settings.min_image_width or height < self.settings.min_image_height:
                        continue
                    image_hash = sha256_bytes(converted)
                    image_id = stable_uuid(f"image:{document_id}:{page_index}:{image_index}:{image_hash}")
                    duplicate_of = seen_hashes.get(image_hash)
                    if duplicate_of is None:
                        seen_hashes[image_hash] = image_id
                    filename = f"{document_id}_page_{page_index}_image_{image_index}.png"
                    image_path = output_dir / filename
                    if duplicate_of is None or not image_path.exists():
                        image_path.write_bytes(converted)
                    images.append(
                        ExtractedImage(
                            document_id=document_id,
                            page_number=page_index,
                            image_id=image_id,
                            image_index=image_index,
                            image_path=image_path,
                            width=width,
                            height=height,
                            file_type="png",
                            image_hash=image_hash,
                            content_type=IMAGE_CONTENT_TYPE,
                            extraction_status="duplicate" if duplicate_of else "extracted",
                            duplicate_of=duplicate_of,
                        )
                    )
                except (KeyError, UnidentifiedImageError, OSError, ValueError) as exc:
                    errors.append(f"page {page_index} image {image_index}: {type(exc).__name__}")
        return images, errors

    def _normalize_text(self, raw_text: str) -> str:
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        normalized = "\n".join(lines)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _to_png(self, image_bytes: bytes) -> tuple[bytes, int, int]:
        with Image.open(io.BytesIO(image_bytes)) as image:
            converted = image.convert("RGB")
            output = io.BytesIO()
            converted.save(output, format="PNG")
            return output.getvalue(), converted.width, converted.height
