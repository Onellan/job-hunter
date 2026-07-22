"""Tests for structured logging."""

from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, request_id_context


def test_json_formatter_includes_correlation_and_extra_fields() -> None:
    """Structured logs preserve contextual request and event information."""

    token = request_id_context.set("request-123")
    try:
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="job_search_completed",
            args=(),
            exc_info=None,
        )
        record.provider = "example"  # type: ignore[attr-defined]

        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_context.reset(token)

    assert payload["message"] == "job_search_completed"
    assert payload["request_id"] == "request-123"
    assert payload["provider"] == "example"
