"""Tests for opt-in notification delivery history without network access."""

from __future__ import annotations

from sqlmodel import Session, SQLModel

from app.database.repositories.notifications import SqliteNotificationRepository
from app.models.notification import NotificationChannel, NotificationStatus
from app.services.notifications import NotificationService


class FailingAdapter:
    """Deterministic adapter that models a transport failure."""

    def send(self, event_type: str) -> None:
        """Reject the test event without performing network I/O."""

        raise OSError(event_type)


def test_failed_notification_is_persisted_without_payload(settings) -> None:  # type: ignore[no-untyped-def]
    """A configured adapter failure creates a safe, queryable audit row."""

    from app.database.engine import create_database_engine

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            service = NotificationService(SqliteNotificationRepository(session))
            result = service.send_test(NotificationChannel.SLACK, FailingAdapter())
            history = service.list_deliveries(0, 25)
    finally:
        engine.dispose()
    assert result.status is NotificationStatus.FAILED
    assert result.error_category == "delivery_failed"
    assert history.total == 1
