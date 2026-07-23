"""Consistent JSON error adapters for application-level failures."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.models.errors import EntityNotFoundError, ResourceConflictError, ResourceValidationError
from app.models.export_errors import ExportUnavailableError


def _browser_error_response(request: Request, status_code: int, message: str) -> HTMLResponse:
    """Render a safe, correlated HTML error for presentation routes only."""

    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "application_name": request.app.state.settings.app.name,
            "version": request.app.state.settings.app.version,
            "csrf_token": getattr(request.state, "csrf_token", ""),
            "current_user": getattr(request.state, "current_user", None),
            "active_page": None,
            "feedback_kind": "error",
            "feedback_message": message,
            "request_id": request.headers.get("X-Request-ID", ""),
            "return_path": request.headers.get("referer", "/dashboard"),
        },
        status_code=status_code,
    )


def _is_browser_request(request: Request) -> bool:
    """Keep the versioned API's JSON error contract independent from the UI."""

    return not request.url.path.startswith("/api/")


async def browser_http_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse | HTMLResponse:
    """Keep browser failures readable while preserving the JSON API contract."""

    assert isinstance(exception, HTTPException)
    if _is_browser_request(request):
        messages = {
            status.HTTP_403_FORBIDDEN: (
                "Your form session has expired. Reload the page and try again."
            ),
            status.HTTP_413_CONTENT_TOO_LARGE: "The submitted form is too large.",
            status.HTTP_422_UNPROCESSABLE_CONTENT: "Check the submitted values and try again.",
            status.HTTP_429_TOO_MANY_REQUESTS: (
                "Too many requests. Wait a moment before trying again."
            ),
        }
        return _browser_error_response(
            request, exception.status_code, messages.get(exception.status_code, "Request failed.")
        )
    return JSONResponse(status_code=exception.status_code, content={"detail": exception.detail})


async def unexpected_error_handler(request: Request, _: Exception) -> JSONResponse | HTMLResponse:
    """Avoid leaking tracebacks or JSON documents into browser pages on a 5xx failure."""

    if _is_browser_request(request):
        return _browser_error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred. Try again or use the reference when reporting it.",
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


async def entity_not_found_handler(
    request: Request, exception: Exception
) -> JSONResponse | HTMLResponse:
    """Translate a missing durable entity into a safe API response."""

    assert isinstance(exception, EntityNotFoundError)
    if _is_browser_request(request):
        return _browser_error_response(
            request, status.HTTP_404_NOT_FOUND, "That item is unavailable."
        )
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exception)})


async def resource_conflict_handler(
    request: Request, exception: Exception
) -> JSONResponse | HTMLResponse:
    """Translate an integrity or lifecycle conflict into an API response."""

    assert isinstance(exception, ResourceConflictError)
    if _is_browser_request(request):
        return _browser_error_response(
            request, status.HTTP_409_CONFLICT, "That change conflicts with current data."
        )
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exception)})


async def resource_validation_handler(
    request: Request, exception: Exception
) -> JSONResponse | HTMLResponse:
    """Translate unavailable configured operations into safe request errors."""

    assert isinstance(exception, ResourceValidationError)
    if _is_browser_request(request):
        return _browser_error_response(
            request, status.HTTP_422_UNPROCESSABLE_CONTENT, str(exception)
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": str(exception)}
    )


async def model_validation_handler(
    request: Request, exception: Exception
) -> JSONResponse | HTMLResponse:
    """Return service-level model validation failures as unprocessable input."""

    assert isinstance(exception, ValidationError)
    if _is_browser_request(request):
        return _browser_error_response(
            request, status.HTTP_422_UNPROCESSABLE_CONTENT, "Check the highlighted form values."
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(exception.errors(include_url=False))},
    )


async def export_unavailable_handler(
    request: Request, exception: Exception
) -> JSONResponse | HTMLResponse:
    """Translate optional export dependency failures into a safe service response."""

    assert isinstance(exception, ExportUnavailableError)
    if _is_browser_request(request):
        return _browser_error_response(
            request, status.HTTP_503_SERVICE_UNAVAILABLE, "Export is temporarily unavailable."
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exception)}
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register application error mappings once at the composition root."""

    application.add_exception_handler(EntityNotFoundError, entity_not_found_handler)
    application.add_exception_handler(ResourceConflictError, resource_conflict_handler)
    application.add_exception_handler(ResourceValidationError, resource_validation_handler)
    application.add_exception_handler(ValidationError, model_validation_handler)
    application.add_exception_handler(ExportUnavailableError, export_unavailable_handler)
    application.add_exception_handler(HTTPException, browser_http_exception_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
