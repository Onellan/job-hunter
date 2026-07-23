"""FastAPI application factory and process entry point."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    AuthenticationMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limits import LoginRateLimiter
from app.database.engine import create_database_engine
from app.database.repositories import SqliteProviderRepository
from app.models.provider import ProviderDefinition
from app.providers.execution import BoundedProviderExecutor
from app.providers.registry import ProviderRegistry
from app.routers.audit import router as audit_router
from app.routers.web import router as web_router
from app.scheduler.runtime import SchedulerRuntime
from app.services.providers import ProviderService

logger = logging.getLogger(__name__)
STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"


def create_app(
    settings: Settings | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> FastAPI:
    """Create a configured Job-Hunter FastAPI application.

    Args:
        settings: Optional validated settings, primarily useful for tests.
        provider_registry: Optional provider registry, primarily useful for deterministic tests.

    Returns:
        A FastAPI application with its infrastructure initialized at lifespan start.
    """

    resolved_settings = settings or get_settings()
    resolved_registry = provider_registry or ProviderRegistry.discover()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Create and dispose process-scoped infrastructure."""

        configure_logging(resolved_settings.logging)
        application.state.settings = resolved_settings
        application.state.engine = create_database_engine(resolved_settings.database)
        # Migrations are applied by the deployment entry point before this
        # application process starts. Bootstrap runs next, before work can be
        # submitted to the executor or scheduler.
        provider_definitions = await asyncio.to_thread(resolved_registry.definitions)
        await asyncio.to_thread(
            _bootstrap_provider_definitions,
            application.state.engine,
            tuple(definition for definition in provider_definitions if definition.bootstrap),
        )
        application.state.provider_availability = {
            definition.code: definition.availability_reason for definition in provider_definitions
        }
        application.state.provider_registry = resolved_registry
        for definition in provider_definitions:
            if definition.availability_reason is not None:
                logger.warning(
                    "provider_runtime_unavailable",
                    extra={
                        "provider_code": definition.code,
                        "category": definition.availability_reason,
                    },
                )
        application.state.login_rate_limiter = LoginRateLimiter(
            resolved_settings.authentication.login_max_attempts,
            resolved_settings.authentication.login_window_seconds,
        )
        application.state.provider_executor = BoundedProviderExecutor(
            application.state.engine,
            resolved_registry,
            resolved_settings.provider_execution,
        )
        application.state.scheduler = SchedulerRuntime(
            application.state.engine,
            resolved_settings.scheduler,
            application.state.provider_executor,
        )
        application.state.scheduler.start()
        logger.info(
            "application_started",
            extra={"environment": resolved_settings.app.environment},
        )
        try:
            yield
        finally:
            application.state.scheduler.shutdown()
            application.state.provider_executor.shutdown()
            application.state.engine.dispose()
            logger.info("application_stopped")

    application = FastAPI(
        title=resolved_settings.app.name,
        version=resolved_settings.app.version,
        debug=resolved_settings.app.debug,
        root_path=resolved_settings.server.root_path,
        lifespan=lifespan,
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=resolved_settings.security.trusted_hosts,
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(AuthenticationMiddleware)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")
    register_exception_handlers(application)
    application.include_router(api_router)
    application.include_router(web_router)
    application.include_router(audit_router)
    return application


app = create_app()


def run() -> None:
    """Run Job-Hunter using the configured host and port values."""

    settings = get_settings()
    uvicorn.run(
        create_app(settings),
        host=settings.server.host,
        port=settings.server.port,
        proxy_headers=True,
    )


def _bootstrap_provider_definitions(
    engine: Engine,
    definitions: tuple[ProviderDefinition, ...],
) -> None:
    """Persist missing discovered providers after migrations and before work starts."""

    with Session(engine) as session:
        ProviderService(SqliteProviderRepository(session)).bootstrap(definitions)
