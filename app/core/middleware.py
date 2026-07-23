"""Small HTTP middleware components used across presentation adapters."""

from __future__ import annotations

import logging
from time import perf_counter
from urllib.parse import parse_qs
from uuid import uuid4

from fastapi import Request, Response
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import request_id_context
from app.core.passwords import token_digest
from app.database.repositories.auth import SqliteAuthRepository
from app.models.common import utc_now

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a correlation identifier to each request and its logs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Set the request identifier for the request lifetime."""

        request_id = request.headers.get("X-Request-ID", uuid4().hex)
        token = request_id_context.set(request_id)
        started_at = perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "http_request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                },
            )
            return response
        finally:
            request_id_context.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative browser security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Set headers that are safe for the application's server-rendered UI."""

        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
        headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net; "
            "script-src 'self' https://unpkg.com; img-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Require opaque local sessions and CSRF tokens when authentication is enabled."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Resolve a session before protected routes without holding it during route work."""

        settings = request.app.state.settings.authentication
        if not settings.enabled or _is_auth_exempt(request.url.path):
            return await call_next(request)
        token = request.cookies.get(settings.session_cookie_name)
        if not token:
            return _unauthenticated_response(request)
        with Session(request.app.state.engine) as session:
            repository = SqliteAuthRepository(session)
            user = repository.get_session(token_digest(token), utc_now())
            if user is None:
                return _unauthenticated_response(request)
            request.state.current_user = user
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                csrf = await _csrf_from_request(request)
                if csrf is None or not repository.csrf_matches(
                    token_digest(token), token_digest(csrf), utc_now()
                ):
                    return Response(status_code=403, content="CSRF validation failed")
            request.state.csrf_token = request.cookies.get("job_hunter_csrf", "")
        return await call_next(request)


def _is_auth_exempt(path: str) -> bool:
    """Allow health, static assets, and the minimal auth bootstrap/login endpoints."""

    return (
        path.startswith("/static/")
        or path == "/api/v1/health"
        or path in {"/api/v1/auth/bootstrap", "/api/v1/auth/login"}
        or path in {"/login", "/login/bootstrap"}
    )


def _unauthenticated_response(request: Request) -> Response:
    """Return API 401 or redirect browser navigation to the local login boundary."""

    if request.url.path.startswith("/api/"):
        return Response(status_code=401, content="Authentication required")
    return Response(status_code=303, headers={"Location": "/login"})


async def _csrf_from_request(request: Request) -> str | None:
    """Read a header or small URL-encoded browser form token from the cached body."""

    header = request.headers.get("X-CSRF-Token")
    if header:
        return header
    if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        values = parse_qs((await request.body()).decode("utf-8"), max_num_fields=120)
        tokens = values.get("csrf_token")
        return tokens[-1] if tokens else None
    return None
