"""Generate a small sample PDF for local manual testing."""

import fitz
from PIL import Image, ImageDraw

from app.core.config import get_settings


def main() -> None:
    """Create a sample PDF with text and one embedded chart-like image."""
    settings = get_settings()
    settings.sample_documents_dir.mkdir(parents=True, exist_ok=True)
    sample_path = settings.sample_documents_dir / "sample_report.pdf"

    image_path = settings.sample_documents_dir / "sample_chart.png"
    image = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(image)
    for idx, height in enumerate([80, 130, 200, 260]):
        x0 = 80 + idx * 120
        draw.rectangle([x0, 320 - height, x0 + 60, 320], fill=(40, 120, 200))
    draw.text((80, 20), "Quarterly revenue growth", fill=(20, 20, 20))
    image.save(image_path)

    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "OmniBrain sample report\n\nRevenue grew across all four quarters, "
        "driven by enterprise subscriptions and improved customer retention.",
        fontsize=12,
    )
    page.insert_image(fitz.Rect(72, 180, 420, 380), filename=str(image_path))
    document.save(sample_path)
    document.close()
    print(f"Created {sample_path}")


if __name__ == "__main__":
    main()
