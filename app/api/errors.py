"""Consistent JSON error adapters for application-level failures."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.errors import EntityNotFoundError, ResourceConflictError


async def entity_not_found_handler(_: Request, exception: Exception) -> JSONResponse:
    """Translate a missing durable entity into a safe API response."""

    assert isinstance(exception, EntityNotFoundError)
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exception)})


async def resource_conflict_handler(_: Request, exception: Exception) -> JSONResponse:
    """Translate an integrity or lifecycle conflict into an API response."""

    assert isinstance(exception, ResourceConflictError)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exception)})


async def model_validation_handler(_: Request, exception: Exception) -> JSONResponse:
    """Return service-level model validation failures as unprocessable input."""

    assert isinstance(exception, ValidationError)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(exception.errors(include_url=False))},
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register application error mappings once at the composition root."""

    application.add_exception_handler(EntityNotFoundError, entity_not_found_handler)
    application.add_exception_handler(ResourceConflictError, resource_conflict_handler)
    application.add_exception_handler(ValidationError, model_validation_handler)
