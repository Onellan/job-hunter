"""Low-memory CSV, JSON, and XLSX renderers for standard job workspace records."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Iterable, Iterator
from io import StringIO
from pathlib import Path
from typing import Any

from app.models.export import ExportDownload
from app.models.export_errors import ExportUnavailableError
from app.models.workspace import JobWorkspaceItem

_JOB_EXPORT_HEADERS = (
    "id",
    "source",
    "source_url",
    "title",
    "company",
    "location",
    "workplace_type",
    "employment_type",
    "description",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "published_at",
    "first_seen_at",
    "last_seen_at",
    "is_bookmarked",
    "is_applied",
    "notes",
)
_STREAM_CHUNK_SIZE = 64 * 1024


class CsvJobExporter:
    """Render job rows as RFC-compatible CSV without accumulating the output."""

    def render(self, jobs: Iterable[JobWorkspaceItem]) -> ExportDownload:
        """Return a lazy CSV download stream for the supplied job iterator."""

        return ExportDownload("job-hunter-jobs.csv", "text/csv; charset=utf-8", _csv_stream(jobs))


class JsonJobExporter:
    """Render a JSON array incrementally so result count does not drive RAM use."""

    def render(self, jobs: Iterable[JobWorkspaceItem]) -> ExportDownload:
        """Return a lazy JSON download stream for the supplied job iterator."""

        return ExportDownload("job-hunter-jobs.json", "application/json", _json_stream(jobs))


class XlsxJobExporter:
    """Write a constant-memory XLSX workbook to a temporary file for download."""

    def render(self, jobs: Iterable[JobWorkspaceItem]) -> ExportDownload:
        """Create a temporary constant-memory workbook and return a deleting stream."""

        xlsxwriter = _load_xlsxwriter()
        path = _temporary_path(".xlsx")
        try:
            workbook = xlsxwriter.Workbook(str(path), {"constant_memory": True})
            worksheet = workbook.add_worksheet("Jobs")
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#1D4ED8", "font_color": "#FFFFFF"}
            )
            worksheet.freeze_panes(1, 0)
            for column_index, header in enumerate(_JOB_EXPORT_HEADERS):
                worksheet.write(0, column_index, header, header_format)
                worksheet.set_column(column_index, column_index, _column_width(header))
            last_row_index = 0
            for row_index, job in enumerate(jobs, start=1):
                for column_index, value in enumerate(
                    _job_export_values(job, spreadsheet_safe=True)
                ):
                    worksheet.write(row_index, column_index, value)
                last_row_index = row_index
            worksheet.autofilter(0, 0, last_row_index, len(_JOB_EXPORT_HEADERS) - 1)
            workbook.close()
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return ExportDownload(
            "job-hunter-jobs.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            _file_stream(path),
        )


def _csv_stream(jobs: Iterable[JobWorkspaceItem]) -> Iterator[bytes]:
    """Yield one CSV row at a time with spreadsheet-formula protection."""

    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(_JOB_EXPORT_HEADERS)
    yield buffer.getvalue().encode("utf-8-sig")
    for job in jobs:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(_job_export_values(job, spreadsheet_safe=True))
        yield buffer.getvalue().encode("utf-8")


def _json_stream(jobs: Iterable[JobWorkspaceItem]) -> Iterator[bytes]:
    """Yield a syntactically valid JSON array without a large intermediate list."""

    yield b"["
    is_first = True
    for job in jobs:
        prefix = b"" if is_first else b","
        encoded = json.dumps(_job_export_mapping(job), ensure_ascii=False, separators=(",", ":"))
        yield prefix + encoded.encode("utf-8")
        is_first = False
    yield b"]"


def _job_export_mapping(job: JobWorkspaceItem) -> dict[str, Any]:
    """Create a stable export mapping while retaining optional provider values."""

    record = job.job
    return {
        "id": str(record.id),
        "source": record.source,
        "source_url": str(record.source_url) if record.source_url else None,
        "title": record.title,
        "company": record.company,
        "location": record.location,
        "workplace_type": record.workplace_type.value,
        "employment_type": record.employment_type.value if record.employment_type else None,
        "description": record.description,
        "salary_min": str(record.salary_min) if record.salary_min is not None else None,
        "salary_max": str(record.salary_max) if record.salary_max is not None else None,
        "salary_currency": record.salary_currency,
        "salary_period": record.salary_period.value if record.salary_period else None,
        "published_at": record.published_at.isoformat() if record.published_at else None,
        "first_seen_at": record.first_seen_at.isoformat(),
        "last_seen_at": record.last_seen_at.isoformat(),
        "is_bookmarked": job.workflow.is_bookmarked,
        "is_applied": job.workflow.is_applied,
        "notes": job.workflow.notes,
    }


def _job_export_values(job: JobWorkspaceItem, spreadsheet_safe: bool) -> list[object]:
    """Return ordered export cells, shielding spreadsheet parsers from formula input."""

    values = list(_job_export_mapping(job).values())
    return [_spreadsheet_value(value) if spreadsheet_safe else value for value in values]


def _spreadsheet_value(value: object) -> object:
    """Prevent provider text from being evaluated as a spreadsheet formula."""

    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _load_xlsxwriter() -> Any:
    """Import the optional production XLSX writer only when an XLSX export is requested."""

    try:
        import xlsxwriter  # type: ignore[import-untyped]
    except ModuleNotFoundError as exception:
        raise ExportUnavailableError(
            "XLSX export requires the optional exports dependency group."
        ) from exception
    return xlsxwriter


def _temporary_path(suffix: str) -> Path:
    """Reserve a unique temporary path without retaining an open Windows handle."""

    descriptor, raw_path = tempfile.mkstemp(prefix="job-hunter-export-", suffix=suffix)
    os.close(descriptor)
    return Path(raw_path)


def _file_stream(path: Path) -> Iterator[bytes]:
    """Yield a temporary file in fixed chunks and remove it after the response ends."""

    try:
        with path.open("rb") as export_file:
            while chunk := export_file.read(_STREAM_CHUNK_SIZE):
                yield chunk
    finally:
        path.unlink(missing_ok=True)


def _column_width(header: str) -> int:
    """Use conservative fixed widths instead of memory-heavy worksheet autofit."""

    widths = {"description": 60, "notes": 40, "source_url": 45, "title": 32, "company": 24}
    return widths.get(header, 18)
