"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "OmniBrain"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_host: str = "0.0.0.0"  # noqa: S104 - Docker/local dev bind host is configurable.
    app_port: int = 8000
    app_log_level: str = "INFO"
    cors_allow_origins: str = "http://localhost:8501"

    database_url: str = "sqlite:///./data/omnibrain.db"

    qdrant_url: str = "http://localhost:6333"
    qdrant_text_collection: str = "omnibrain_text"
    qdrant_image_collection: str = "omnibrain_images"
    qdrant_timeout_seconds: float = 5.0

    text_embedding_provider: str = "local"
    text_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    text_embedding_batch_size: int = 32
    text_embedding_dimension: int = 384

    clip_model: str = "openai/clip-vit-base-patch32"
    image_embedding_batch_size: int = 8
    image_embedding_dimension: int = 512

    max_upload_size_mb: int = 50
    text_chunk_size: int = 800
    text_chunk_overlap: int = 120
    min_text_chunk_chars: int = 40

    min_image_width: int = 150
    min_image_height: int = 150

    upload_dir: Path = Path("data/uploads")
    extracted_images_dir: Path = Path("data/extracted_images")
    sample_documents_dir: Path = Path("data/sample_documents")

    openai_api_key: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """Return comma-separated CORS origins as a list."""
        if not self.cors_allow_origins.strip():
            return []
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Return max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
