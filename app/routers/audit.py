"""Server-rendered audit-history presentation routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.dependencies import get_export_service, get_notification_service
from app.core.config import Settings
from app.services.exports import ExportService
from app.services.notifications import NotificationService

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_HISTORY_PAGE_SIZE = 25


@router.get("/activity", response_class=HTMLResponse)
def activity_page(request: Request) -> HTMLResponse:
    """Render a compact entry point for safe operational audit history."""

    return templates.TemplateResponse(request, "activity.html", _base_context(request))


@router.get("/exports/history", response_class=HTMLResponse)
def export_history_page(
    request: Request,
    service: Annotated[ExportService, Depends(get_export_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HTMLResponse:
    """Render one bounded, privacy-minimised page of export audit events."""

    return templates.TemplateResponse(
        request,
        "export_history.html",
        _base_context(request, events=service.list_events(offset, _HISTORY_PAGE_SIZE)),
    )


@router.get("/notifications/history", response_class=HTMLResponse)
def notification_history_page(
    request: Request,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HTMLResponse:
    """Render one bounded page of delivery outcomes without sensitive values."""

    return templates.TemplateResponse(
        request,
        "notification_history.html",
        _base_context(request, deliveries=service.list_deliveries(offset, _HISTORY_PAGE_SIZE)),
    )


def _base_context(request: Request, **context: object) -> dict[str, object]:
    """Supply shared presentation metadata without coupling audit routes to web routes."""

    settings: Settings = request.app.state.settings
    return {
        "application_name": settings.app.name,
        "version": settings.app.version,
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "current_user": getattr(request.state, "current_user", None),
        "active_page": "activity",
        **context,
    }
