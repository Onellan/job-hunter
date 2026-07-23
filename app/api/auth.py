"""Local bootstrap and login API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core.passwords import token_digest
from app.database.engine import get_session
from app.database.repositories.auth import SqliteAuthRepository
from app.models.auth import Credentials, UserRecord
from app.services.authentication import AuthenticationService

router = APIRouter(prefix="/auth", tags=["authentication"])


def _service(request: Request, session: Session) -> AuthenticationService:
    """Compose local authentication from request-scoped persistence."""
    return AuthenticationService(
        SqliteAuthRepository(session), request.app.state.settings.authentication.session_ttl_hours
    )


@router.post("/bootstrap", response_model=UserRecord, status_code=status.HTTP_201_CREATED)
def bootstrap(
    credentials: Credentials, request: Request, session: Annotated[Session, Depends(get_session)]
) -> UserRecord:
    """Create the sole local account once when authentication is enabled."""
    return _service(request, session).bootstrap(credentials)


@router.post("/login", response_model=UserRecord)
def login(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> UserRecord:
    """Issue opaque HttpOnly session and readable CSRF cookies after credential verification."""
    client_key = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_rate_limiter
    limit = limiter.check(client_key)
    if not limit.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(limit.retry_after_seconds)},
        )
    authenticated = _service(request, session).login(credentials)
    if authenticated is None:
        limiter.record_failure(client_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    limiter.clear(client_key)
    token, csrf = authenticated.csrf_token.split(".", 1)
    settings = request.app.state.settings.authentication
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    response.set_cookie(
        "job_hunter_csrf",
        csrf,
        httponly=False,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return authenticated.user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request, response: Response, session: Annotated[Session, Depends(get_session)]
) -> Response:
    """Invalidate the current opaque session if present and clear matching cookies."""
    settings = request.app.state.settings.authentication
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        SqliteAuthRepository(session).delete_session(token_digest(token))
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie("job_hunter_csrf")
    return response
