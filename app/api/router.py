"""Versioned JSON API router composition."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.provider_runs import router as provider_runs_router
from app.api.providers import router as providers_router
from app.api.searches import router as searches_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(providers_router)
api_router.include_router(searches_router)
api_router.include_router(provider_runs_router)
