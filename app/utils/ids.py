"""Stable ID helpers."""

from uuid import NAMESPACE_URL, uuid5


def stable_uuid(value: str) -> str:
    """Generate a deterministic UUID from a stable string."""
    return str(uuid5(NAMESPACE_URL, value))
