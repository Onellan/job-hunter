"""Expected errors at the optional export dependency and backup boundaries."""

from __future__ import annotations


class ExportUnavailableError(RuntimeError):
    """Raised when an optional exporter or a safe database backup is unavailable."""
