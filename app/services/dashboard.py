"""Application service for the compact dashboard read model."""

from __future__ import annotations

from app.models.common import utc_now
from app.models.dashboard import DashboardSnapshot
from app.services.ports import DashboardRepository


class DashboardService:
    """Coordinate a bounded dashboard snapshot without persistence details."""

    def __init__(self, repository: DashboardRepository) -> None:
        """Create the dashboard service with a read-model repository."""

        self._repository = repository

    def get_snapshot(self) -> DashboardSnapshot:
        """Return today's persisted dashboard information in UTC."""

        now = utc_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return self._repository.get_snapshot(today_start)
