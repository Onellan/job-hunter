"""Browser-route regression tests for privacy-minimised audit history."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database.repositories.notifications import SqliteNotificationRepository
from app.models.common import utc_now
from app.models.notification import NotificationChannel, NotificationStatus


def test_activity_navigation_and_empty_history_pages(api_client: TestClient) -> None:
    """Primary navigation announces the current route and empty audit pages are useful."""

    dashboard = api_client.get("/dashboard")
    activity = api_client.get("/activity")
    exports = api_client.get("/exports/history")
    notifications = api_client.get("/notifications/history")

    assert 'href="/dashboard" aria-current="page"' in dashboard.text
    assert 'href="/activity" aria-current="page"' in activity.text
    assert "No exports have been requested yet." in exports.text
    assert "No notification deliveries have been recorded yet." in notifications.text


def test_audit_history_renders_safe_populated_metadata(api_client: TestClient) -> None:
    """Export and delivery pages render durable safe metadata without sensitive content."""

    export = api_client.get("/exports/jobs", params={"format": "csv"})
    with Session(api_client.app.state.engine) as session:
        SqliteNotificationRepository(session).create_delivery(
            NotificationChannel.SLACK,
            "notification_test",
            NotificationStatus.FAILED,
            "delivery_failed",
            utc_now(),
        )

    exports = api_client.get("/exports/history")
    notifications = api_client.get("/notifications/history")

    assert export.status_code == 200
    assert "CSV" in exports.text
    assert "Jobs" in exports.text
    assert "Slack" in notifications.text
    assert "Delivery Failed" not in notifications.text
    assert "delivery_failed" in notifications.text
    assert "webhook" not in notifications.text.lower()
