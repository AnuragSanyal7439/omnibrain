"""Hashing utilities."""

import hashlib
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    """Return SHA-256 hash for bytes."""
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return SHA-256 hash for a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()
