"""SQLite persistence for privacy-minimised notification delivery history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func
from sqlmodel import Session, select

from app.database.mappers import to_notification_delivery_record
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import NotificationDeliveryTable
from app.models.common import PaginatedResult
from app.models.notification import (
    NotificationChannel,
    NotificationDeliveryRecord,
    NotificationStatus,
)


class SqliteNotificationRepository:
    """Persist delivery outcomes without message content, targets, or credentials."""

    def __init__(self, session: Session) -> None:
        """Create the repository with one request-scoped database session."""

        self._session = session

    def create_delivery(
        self,
        channel: NotificationChannel,
        event_type: str,
        status: NotificationStatus,
        error_category: str | None,
        now: datetime,
    ) -> NotificationDeliveryRecord:
        """Persist a completed delivery outcome after an adapter attempt."""

        table = NotificationDeliveryTable(
            channel=channel.value,
            event_type=event_type,
            status=status.value,
            error_category=error_category,
            created_at=now,
            finished_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_notification_delivery_record(table)

    def list_deliveries(
        self, offset: int, limit: int
    ) -> PaginatedResult[NotificationDeliveryRecord]:
        """Return a bounded newest-first delivery audit page."""

        tables = self._session.exec(
            select(NotificationDeliveryTable)
            .order_by(
                desc(NotificationDeliveryTable.created_at), desc(NotificationDeliveryTable.id)
            )
            .offset(offset)
            .limit(limit)
        ).all()
        total = self._session.exec(
            select(func.count()).select_from(NotificationDeliveryTable)
        ).one()
        return PaginatedResult(
            items=[to_notification_delivery_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )
