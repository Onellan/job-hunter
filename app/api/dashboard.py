"""Versioned JSON endpoint for the compact workspace dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_dashboard_service
from app.models.dashboard import DashboardSnapshot
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSnapshot)
def get_dashboard(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardSnapshot:
    """Return bounded dashboard metrics and latest workspace records."""

    return service.get_snapshot()
