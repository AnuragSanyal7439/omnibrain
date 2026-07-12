"""Database engine and session helpers."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base


def _create_engine() -> Engine:
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(settings.database_url, connect_args={"check_same_thread": False})
    return create_engine(settings.database_url)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> dict[str, bool | str]:
    """Check database connectivity."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"ready": True, "message": "SQLite connection is healthy"}
    except Exception:
        return {"ready": False, "message": "SQLite connection failed"}
