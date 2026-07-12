"""CLIP image embedding service."""

from importlib.util import find_spec
from pathlib import Path
from typing import Any, Protocol

from fastapi import status
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import AppError, ErrorCode


class ImageEmbeddingProvider(Protocol):
    """Image embedding provider interface."""

    dimension: int

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]:
        """Embed images."""
        ...

    def embed_text_query(self, text: str) -> list[float]:
        """Embed text query in the image model's semantic space."""
        ...

    def check_ready(self) -> dict[str, bool | str]:
        """Return provider readiness."""
        ...


class ClipImageEmbeddingProvider:
    """CLIP provider backed by transformers."""

    def __init__(self, model_name: str, batch_size: int, expected_dimension: int) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.dimension = expected_dimension
        self._model: Any | None = None
        self._processor: Any | None = None
        self._torch: Any | None = None

    def _load_model(self) -> tuple[Any, Any, Any]:
        if self._model is None or self._processor is None or self._torch is None:
            try:
                import torch
                from transformers import CLIPModel, CLIPProcessor

                self._processor = CLIPProcessor.from_pretrained(self.model_name)
                self._model = CLIPModel.from_pretrained(self.model_name)
                self._model.eval()
                self._torch = torch
            except Exception as exc:
                raise AppError(
                    ErrorCode.EMBEDDING_FAILURE,
                    "Failed to load CLIP image embedding model",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc
        return self._model, self._processor, self._torch

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]:
        """Embed image files with CLIP."""
        if not image_paths:
            return []
        model, processor, torch = self._load_model()
        vectors: list[list[float]] = []
        for start in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[start : start + self.batch_size]
            images = [Image.open(path).convert("RGB") for path in batch_paths]
            inputs = processor(images=images, return_tensors="pt", padding=True)  # type: ignore[operator]
            with torch.no_grad():
                features = model.get_image_features(**inputs)  # type: ignore[attr-defined]
                features = features / features.norm(dim=-1, keepdim=True)
            vectors.extend(features.cpu().numpy().astype(float).tolist())
        self._validate_dimensions(vectors)
        return vectors

    def embed_text_query(self, text: str) -> list[float]:
        """Embed a natural-language image search query using CLIP text encoder."""
        model, processor, torch = self._load_model()
        inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)  # type: ignore[operator]
        with torch.no_grad():
            features = model.get_text_features(**inputs)  # type: ignore[attr-defined]
            features = features / features.norm(dim=-1, keepdim=True)
        vector = features.cpu().numpy()[0].astype(float).tolist()
        self._validate_dimensions([vector])
        return vector

    def check_ready(self) -> dict[str, bool | str]:
        """Check whether CLIP dependencies are importable.

        Model weights are loaded lazily during ingestion/search so readiness does
        not trigger large downloads or expensive imports.
        """
        missing = [module for module in ("transformers", "torch", "PIL") if find_spec(module) is None]
        if missing:
            return {"ready": False, "message": f"Missing CLIP dependencies: {', '.join(missing)}"}
        return {"ready": True, "message": "CLIP image embedding provider is configured"}

    def _validate_dimensions(self, vectors: list[list[float]]) -> None:
        for vector in vectors:
            if len(vector) != self.dimension:
                raise AppError(
                    ErrorCode.EMBEDDING_FAILURE,
                    f"Image embedding dimension mismatch: expected {self.dimension}, got {len(vector)}",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


class ImageEmbeddingService:
    """Facade for image and text-to-image query embeddings."""

    def __init__(self, provider: ImageEmbeddingProvider | None = None) -> None:
        settings = get_settings()
        self.provider = provider or ClipImageEmbeddingProvider(
            settings.clip_model,
            settings.image_embedding_batch_size,
            settings.image_embedding_dimension,
        )

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]:
        """Embed extracted images."""
        return self.provider.embed_images(image_paths)

    def embed_text_query(self, text: str) -> list[float]:
        """Embed image-search text query."""
        return self.provider.embed_text_query(text)

    def check_ready(self) -> dict[str, bool | str]:
        """Return image provider readiness."""
        return self.provider.check_ready()
