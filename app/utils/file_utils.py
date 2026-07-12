"""Filesystem safety helpers."""

import re
from pathlib import Path

from app.core.config import get_settings


def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filenames while keeping readable names."""
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "document.pdf"


def ensure_storage_dirs() -> None:
    """Create configured data directories."""
    settings = get_settings()
    for path in (settings.upload_dir, settings.extracted_images_dir, settings.sample_documents_dir):
        path.mkdir(parents=True, exist_ok=True)


def remove_path_safely(path: Path, allowed_roots: list[Path]) -> None:
    """Remove a file only if it is under an allowed storage root."""
    if not path.exists():
        return
    resolved = path.resolve()
    allowed = [root.resolve() for root in allowed_roots]
    if not any(resolved.is_relative_to(root) for root in allowed):
        raise ValueError(f"Refusing to delete path outside managed storage: {path}")
    if path.is_file():
        path.unlink()
