"""Reset local OmniBrain storage for development."""

from pathlib import Path

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine


def main() -> None:
    """Drop database tables and remove generated storage files."""
    settings = get_settings()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    for directory in (settings.upload_dir, settings.extracted_images_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for path in directory.iterdir():
            if path.name == ".gitkeep":
                continue
            if path.is_file():
                path.unlink()
    db_path = Path(settings.database_url.replace("sqlite:///", "", 1))
    print(f"Storage reset. Database: {db_path}")


if __name__ == "__main__":
    main()
