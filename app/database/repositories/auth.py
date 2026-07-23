"""SQLite persistence for local users and expiring sessions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import SessionTable, UserTable
from app.models.auth import UserRecord


class SqliteAuthRepository:
    """Persist safe local authentication state with short transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def user_count(self) -> int:
        """Return whether local bootstrap has already occurred."""
        return len(self._session.exec(select(UserTable.id).limit(1)).all())

    def create_user(self, username: str, password_hash: str, now: datetime) -> UserRecord:
        """Create one local user and return only safe fields."""
        table = UserTable(username=username, password_hash=password_hash, created_at=now)
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return UserRecord(id=table.id, username=table.username, created_at=table.created_at)

    def get_user_credentials(self, username: str) -> tuple[UserRecord, str] | None:
        """Return safe user data and its verifier only for credential checking."""
        table = self._session.exec(select(UserTable).where(UserTable.username == username)).first()
        if table is None:
            return None
        return (
            UserRecord(id=table.id, username=table.username, created_at=table.created_at),
            table.password_hash,
        )

    def create_session(
        self, user_id: UUID, token: str, csrf: str, expires_at: datetime, now: datetime
    ) -> None:
        """Persist digests only; raw browser tokens never enter the database."""
        table = SessionTable(
            user_id=user_id,
            token_digest=token,
            csrf_digest=csrf,
            expires_at=expires_at,
            created_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)

    def get_session(self, token_digest: str, now: datetime) -> UserRecord | None:
        """Return the session user when a non-expired token digest exists."""
        row = self._session.exec(
            select(SessionTable, UserTable)
            .join(UserTable, UserTable.id == SessionTable.user_id)
            .where(SessionTable.token_digest == token_digest, SessionTable.expires_at > now)
        ).first()
        if row is None:
            return None
        _, user = row
        return UserRecord(id=user.id, username=user.username, created_at=user.created_at)

    def csrf_matches(self, token_digest: str, csrf_digest: str, now: datetime) -> bool:
        """Check a CSRF token against the live session without exposing either digest."""
        row = self._session.exec(
            select(SessionTable.id).where(
                SessionTable.token_digest == token_digest,
                SessionTable.csrf_digest == csrf_digest,
                SessionTable.expires_at > now,
            )
        ).first()
        return row is not None

    def delete_session(self, token_digest: str) -> None:
        """Invalidate one session if it remains present."""
        table = self._session.exec(
            select(SessionTable).where(SessionTable.token_digest == token_digest)
        ).first()
        if table is not None:
            self._session.delete(table)
            commit_or_raise_conflict(self._session)
