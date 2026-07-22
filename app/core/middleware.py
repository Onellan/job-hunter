"""Small HTTP middleware components used across presentation adapters."""

from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import request_id_context

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
        return response
