"""Versioned API endpoints for opt-in notification verification and history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.database.engine import get_session
from app.database.repositories.notifications import SqliteNotificationRepository
from app.models.common import PaginatedResult
from app.models.notification import NotificationDeliveryRecord, NotificationTestRequest
from app.notifications.adapters import configured_adapter
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _service(session: Session) -> NotificationService:
    """Compose notification use cases with a request-scoped SQLite repository."""

    return NotificationService(SqliteNotificationRepository(session))


@router.post(
    "/test", response_model=NotificationDeliveryRecord, status_code=status.HTTP_201_CREATED
)
def send_test_notification(
    payload: NotificationTestRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> NotificationDeliveryRecord:
    """Attempt one configured channel and persist its payload-free outcome."""

    return _service(session).send_test(
        payload.channel,
        configured_adapter(request.app.state.settings.notifications, payload.channel),
    )


@router.get("/deliveries", response_model=PaginatedResult[NotificationDeliveryRecord])
def list_notification_deliveries(
    session: Annotated[Session, Depends(get_session)],
    offset: int = 0,
    limit: int = 25,
) -> PaginatedResult[NotificationDeliveryRecord]:
    """Return a bounded notification delivery history without sensitive content."""

    return _service(session).list_deliveries(offset, min(limit, 100))
