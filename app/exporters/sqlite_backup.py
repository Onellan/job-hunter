"""SQLite online backup exporter that creates a consistent temporary database copy."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url

from app.exporters.jobs import _file_stream, _temporary_path
from app.models.export import ExportDownload
from app.models.export_errors import ExportUnavailableError


class SqliteBackupExporter:
    """Create an online SQLite backup without loading the database into memory."""

    def __init__(self, database_url: str) -> None:
        """Select the configured SQLite database URL used by the running application."""

        self._database_url = database_url

    def render(self) -> ExportDownload:
        """Write a consistent SQLite backup to a temporary file and stream it once."""

        source_path = _sqlite_source_path(self._database_url)
        target_path = _temporary_path(".sqlite")
        try:
            source_connection = sqlite3.connect(source_path)
            target_connection = sqlite3.connect(target_path)
            try:
                source_connection.backup(target_connection, pages=100)
            finally:
                target_connection.close()
                source_connection.close()
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        return ExportDownload(
            "job-hunter-backup.sqlite",
            "application/vnd.sqlite3",
            _file_stream(target_path),
        )


def _sqlite_source_path(database_url: str) -> str:
    """Validate and resolve only file-backed SQLite databases for online backup."""

    url = make_url(database_url)
    database = url.database
    if not url.drivername.startswith("sqlite") or database is None or database == ":memory:":
        raise ExportUnavailableError("SQLite backup export requires a file-backed SQLite database.")
    source_path = Path(database)
    if not source_path.is_file():
        raise ExportUnavailableError(
            "The configured SQLite database file is not available for backup."
        )
    return str(source_path)
