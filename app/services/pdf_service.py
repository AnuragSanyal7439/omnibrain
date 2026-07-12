"""PDF text and embedded image extraction service."""

import io
import re
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.constants import IMAGE_CONTENT_TYPE
from app.core.exceptions import AppError, ErrorCode
from app.utils.hashing import sha256_bytes
from app.utils.ids import stable_uuid


@dataclass(frozen=True)
class PageText:
    """Extracted text for a single 1-based PDF page."""

    document_id: str
    page_number: int
    text: str
    character_count: int
    requires_ocr: bool
    extraction_status: str


@dataclass(frozen=True)
class ExtractedImage:
    """Metadata for an extracted raster image."""

    document_id: str
    page_number: int
    image_id: str
    image_index: int
    image_path: Path
    width: int
    height: int
    file_type: str
    image_hash: str
    content_type: str
    extraction_status: str
    duplicate_of: str | None = None


class PdfService:
    """Extract text and embedded images from PDF documents."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def extract_text(self, pdf_path: Path, document_id: str) -> list[PageText]:
        """Extract normalized text records from every PDF page."""
        pages: list[PageText] = []
        try:
            with fitz.open(pdf_path) as document:
                for index, page in enumerate(document, start=1):
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
        except Exception as exc:
            raise AppError(ErrorCode.INVALID_PDF, "PDF could not be parsed") from exc
        return pages

    def extract_images(self, pdf_path: Path, document_id: str) -> tuple[list[ExtractedImage], list[str]]:
        """Extract embedded raster images while keeping page-level metadata."""
        output_dir = self.settings.extracted_images_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        images: list[ExtractedImage] = []
        errors: list[str] = []
        seen_hashes: dict[str, str] = {}

        try:
            with fitz.open(pdf_path) as document:
                for page_index, page in enumerate(document, start=1):
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
        except Exception as exc:
            raise AppError(ErrorCode.INVALID_PDF, "PDF images could not be inspected") from exc
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
