"""Structured logging utilities."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Attach request IDs to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def configure_logging(level: str) -> None:
    """Configure application logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(fmt=("%(asctime)s %(levelname)s [%(name)s] " "request_id=%(request_id)s %(message)s"))
    )
    handler.addFilter(RequestIdFilter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
    logging.getLogger("uvicorn.access").addFilter(RequestIdFilter())


def log_extra(**kwargs: Any) -> str:
    """Serialize key-value details for safe structured logs."""
    return " ".join(f"{key}={value}" for key, value in kwargs.items())
