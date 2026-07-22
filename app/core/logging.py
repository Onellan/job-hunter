"""Structured logging helpers with request correlation support."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import LoggingSettings

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

_STANDARD_LOG_RECORD_ATTRIBUTES = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "getMessage",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """Format log records as compact JSON suitable for aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize one logging record as JSON."""

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_context.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_LOG_RECORD_ATTRIBUTES and not key.startswith("_")
            }
        )
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(settings: LoggingSettings) -> None:
    """Configure root logging once for the running application.

    Args:
        settings: The validated logging configuration.
    """

    handler = logging.StreamHandler()
    formatter = JsonFormatter() if settings.json_logs else logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.level.upper())
