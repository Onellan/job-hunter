"""Shared, small persistence helpers for SQLModel repositories."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.errors import ResourceConflictError


def commit_or_raise_conflict(session: Session) -> None:
    """Commit a short transaction and convert integrity failures to domain errors."""

    try:
        session.commit()
    except IntegrityError as exception:
        session.rollback()
        raise ResourceConflictError("The operation conflicts with existing data") from exception
