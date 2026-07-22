"""Server-rendered web routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import Settings

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request) -> HTMLResponse:
    """Render the lightweight application landing page."""

    settings: Settings = request.app.state.settings
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"application_name": settings.app.name, "version": settings.app.version},
    )
