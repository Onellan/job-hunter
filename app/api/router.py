"""Versioned JSON API router composition."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.notifications import router as notifications_router
from app.api.provider_runs import router as provider_runs_router
from app.api.providers import router as providers_router
from app.api.resume import router as resume_router
from app.api.schedules import router as schedules_router
from app.api.searches import router as searches_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(notifications_router)
api_router.include_router(resume_router)
api_router.include_router(dashboard_router)
api_router.include_router(exports_router)
api_router.include_router(jobs_router)
api_router.include_router(providers_router)
api_router.include_router(searches_router)
api_router.include_router(schedules_router)
api_router.include_router(provider_runs_router)
