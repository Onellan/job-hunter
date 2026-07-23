"""Local authentication use cases with password verification and expiring sessions."""

from __future__ import annotations

from datetime import timedelta

from app.core.passwords import hash_password, new_token, token_digest, verify_password
from app.database.repositories.auth import SqliteAuthRepository
from app.models.auth import AuthenticatedSession, Credentials, UserRecord
from app.models.common import utc_now
from app.models.errors import ResourceConflictError


class AuthenticationService:
    """Bootstrap one local user and issue or invalidate secure session tokens."""

    def __init__(self, repository: SqliteAuthRepository, session_ttl_hours: int) -> None:
        self._repository = repository
        self._session_ttl_hours = session_ttl_hours

    def bootstrap(self, credentials: Credentials) -> UserRecord:
        """Create the first user exactly once."""
        if self._repository.user_count():
            raise ResourceConflictError("A local user already exists")
        return self._repository.create_user(
            credentials.username, hash_password(credentials.password), utc_now()
        )

    def login(self, credentials: Credentials) -> AuthenticatedSession | None:
        """Verify credentials and create an expiring session when they are valid."""
        found = self._repository.get_user_credentials(credentials.username)
        if found is None or not verify_password(credentials.password, found[1]):
            return None
        token, csrf = new_token(), new_token()
        now = utc_now()
        self._repository.create_session(
            found[0].id,
            token_digest(token),
            token_digest(csrf),
            now + timedelta(hours=self._session_ttl_hours),
            now,
        )
        return AuthenticatedSession(user=found[0], csrf_token=f"{token}.{csrf}")
