"""Versioned JSON endpoints for recurring saved-search schedules."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.api.dependencies import get_schedule_service
from app.models.common import PaginatedResult
from app.models.schedule import ScheduleCreate, ScheduleRecord, ScheduleRunRecord, ScheduleUpdate
from app.scheduler.runtime import SchedulerRuntime
from app.services.schedules import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleRecord, status_code=status.HTTP_201_CREATED)
def create_schedule(
    schedule: ScheduleCreate,
    request: Request,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> ScheduleRecord:
    """Persist and register a recurring schedule."""

    created = service.create(schedule)
    _runtime(request).sync(created)
    return created


@router.get("", response_model=PaginatedResult[ScheduleRecord])
def list_schedules(
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResult[ScheduleRecord]:
    """Return a bounded page of durable schedules."""

    return service.list(offset, limit)


@router.get("/{schedule_id}", response_model=ScheduleRecord)
def get_schedule(
    schedule_id: UUID,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> ScheduleRecord:
    """Return one schedule."""

    return service.get(schedule_id)


@router.patch("/{schedule_id}", response_model=ScheduleRecord)
def update_schedule(
    schedule_id: UUID,
    changes: ScheduleUpdate,
    request: Request,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> ScheduleRecord:
    """Persist and re-register a modified recurring schedule."""

    updated = service.update(schedule_id, changes)
    _runtime(request).sync(updated)
    return updated


@router.post("/{schedule_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_schedule_now(schedule_id: UUID, request: Request) -> Response:
    """Queue one immediate schedule dispatch without waiting for provider work."""

    _runtime(request).run_now(schedule_id)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.get("/{schedule_id}/runs", response_model=PaginatedResult[ScheduleRunRecord])
def list_schedule_runs(
    schedule_id: UUID,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResult[ScheduleRunRecord]:
    """Return bounded durable dispatch history for one schedule."""

    return service.list_runs(schedule_id, offset, limit)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    request: Request,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> Response:
    """Remove a recurring trigger while retaining its historical run records."""

    service.delete(schedule_id)
    _runtime(request).remove(schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _runtime(request: Request) -> SchedulerRuntime:
    """Return the process-scoped scheduler adapter composed at application startup."""

    return cast(SchedulerRuntime, request.app.state.scheduler)
