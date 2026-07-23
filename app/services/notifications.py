"""Notification delivery use cases and safe failure classification."""

from __future__ import annotations

import smtplib

from app.database.repositories.notifications import SqliteNotificationRepository
from app.models.common import PaginatedResult, utc_now
from app.models.errors import ResourceValidationError
from app.models.notification import (
    NotificationChannel,
    NotificationDeliveryRecord,
    NotificationStatus,
)
from app.notifications.adapters import NotificationAdapter


class NotificationService:
    """Send opt-in operational notifications and retain only delivery metadata."""

    def __init__(self, repository: SqliteNotificationRepository) -> None:
        """Create the service with a durable notification-history repository."""

        self._repository = repository

    def send_test(
        self, channel: NotificationChannel, adapter: NotificationAdapter | None
    ) -> NotificationDeliveryRecord:
        """Attempt one configured test delivery and safely record its outcome."""

        if adapter is None:
            raise ResourceValidationError("The requested notification channel is not configured")
        try:
            adapter.send("notification_test")
        except (OSError, ValueError, smtplib.SMTPException):
            return self._repository.create_delivery(
                channel,
                "notification_test",
                NotificationStatus.FAILED,
                "delivery_failed",
                utc_now(),
            )
        return self._repository.create_delivery(
            channel, "notification_test", NotificationStatus.SUCCEEDED, None, utc_now()
        )

    def list_deliveries(
        self, offset: int, limit: int
    ) -> PaginatedResult[NotificationDeliveryRecord]:
        """List bounded delivery history without payload or recipient data."""

        return self._repository.list_deliveries(offset, limit)
