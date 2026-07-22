"""System health API contracts and endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.database.engine import is_database_available

router = APIRouter(tags=["system"])


class ComponentHealth(BaseModel):
    """Health status for an individual infrastructure component."""

    status: Literal["ok", "unavailable"]


class HealthResponse(BaseModel):
    """A small, stable readiness response for users and orchestrators."""

    status: Literal["ok", "degraded"]
    application: str
    version: str
    environment: str
    database: ComponentHealth


@router.get("/health", response_model=HealthResponse, summary="Check application health")
def get_health(request: Request) -> HealthResponse:
    """Report application metadata and the current database connectivity state."""

    settings: Settings = request.app.state.settings
    engine: Engine = request.app.state.engine
    database_available = is_database_available(engine)
    return HealthResponse(
        status="ok" if database_available else "degraded",
        application=settings.app.name,
        version=settings.app.version,
        environment=settings.app.environment,
        database=ComponentHealth(status="ok" if database_available else "unavailable"),
    )
