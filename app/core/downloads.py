"""Safe HTTP adapters for application-level streaming file downloads."""

from __future__ import annotations

from fastapi.responses import StreamingResponse

from app.models.export import ExportDownload


def download_response(download: ExportDownload) -> StreamingResponse:
    """Translate an export download into an attachment response without buffering bytes."""

    return StreamingResponse(
        download.content,
        media_type=download.media_type,
        headers={"Content-Disposition": f'attachment; filename="{download.filename}"'},
    )
