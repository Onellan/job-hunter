"""Server-rendered and HTMX presentation routes for the job workspace."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated
from urllib.parse import parse_qs, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from app.api.dependencies import (
    get_dashboard_service,
    get_export_service,
    get_job_scoring_service,
    get_job_workspace_service,
    get_resume_matching_service,
)
from app.core.config import Settings
from app.core.downloads import download_response
from app.database.repositories.auth import SqliteAuthRepository
from app.models.auth import Credentials
from app.models.errors import EntityNotFoundError
from app.models.export import JobExportRequest
from app.models.matching import JobComparisonRequest, ResumeUploadRequest
from app.models.workspace import BulkJobWorkflowUpdate, JobWorkflowUpdate, JobWorkspaceQuery
from app.services.authentication import AuthenticationService
from app.services.dashboard import DashboardService
from app.services.exports import ExportService
from app.services.matching import ResumeMatchingService
from app.services.scoring import JobScoringService
from app.services.workspace import JobWorkspaceService

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_MAX_FORM_BYTES = 210_000


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    """Render the local login and one-time bootstrap form."""

    return templates.TemplateResponse(
        request=request, name="login.html", context=_base_context(request)
    )


@router.post("/login")
async def login_form(request: Request) -> Response:
    """Authenticate a browser form and issue the same session cookies as the API."""

    fields = await _form_fields(request)
    credentials = _validated_model(
        Credentials, {"username": _last(fields, "username"), "password": _last(fields, "password")}
    )
    client_key = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_rate_limiter
    if not limiter.check(client_key).allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts"
        )
    with Session(request.app.state.engine) as session:
        service = AuthenticationService(
            SqliteAuthRepository(session),
            request.app.state.settings.authentication.session_ttl_hours,
        )
        authenticated = service.login(credentials)
    if authenticated is None:
        limiter.record_failure(client_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    limiter.clear(client_key)
    return _authenticated_redirect(request, authenticated.csrf_token)


@router.post("/login/bootstrap")
async def bootstrap_form(request: Request) -> Response:
    """Create the first local account from the browser login boundary."""

    fields = await _form_fields(request)
    credentials = _validated_model(
        Credentials, {"username": _last(fields, "username"), "password": _last(fields, "password")}
    )
    with Session(request.app.state.engine) as session:
        AuthenticationService(
            SqliteAuthRepository(session),
            request.app.state.settings.authentication.session_ttl_hours,
        ).bootstrap(credentials)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> HTMLResponse:
    """Render the dashboard page with a compact durable snapshot."""

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_base_context(request, dashboard=service.get_snapshot()),
    )


@router.get("/dashboard/summary", response_class=HTMLResponse)
def dashboard_summary(
    request: Request,
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> HTMLResponse:
    """Render only the dashboard summary for low-cost HTMX refreshes."""

    return templates.TemplateResponse(
        request=request,
        name="fragments/dashboard_summary.html",
        context=_base_context(request, dashboard=service.get_snapshot()),
    )


@router.get("/matching", response_class=HTMLResponse)
def matching_page(
    request: Request,
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> HTMLResponse:
    """Render local consent, extracted skills, and bounded job comparison controls."""

    try:
        profile = service.get_profile()
    except EntityNotFoundError:
        profile = None
    return templates.TemplateResponse(
        request=request,
        name="matching.html",
        context=_base_context(request, profile=profile, comparison=None),
    )


@router.post("/matching/resume")
async def upload_resume_form(
    request: Request,
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> Response:
    """Extract consented resume skills from the progressive browser form."""

    fields = await _form_fields(request)
    profile = service.upload(
        _validated_model(
            ResumeUploadRequest,
            {"consent": _last(fields, "consent") == "true", "content": _last(fields, "content")},
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="fragments/resume_profile.html",
        context=_base_context(request, profile=profile),
    )


@router.post("/matching/compare", response_class=HTMLResponse)
async def compare_jobs_form(
    request: Request,
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> HTMLResponse:
    """Render an on-demand comparison using comma-separated selected job identifiers."""

    fields = await _form_fields(request)
    job_ids = [
        value.strip() for value in (_last(fields, "job_ids") or "").split(",") if value.strip()
    ]
    comparison = service.compare(_validated_model(JobComparisonRequest, {"job_ids": job_ids}))
    return templates.TemplateResponse(
        request=request,
        name="fragments/job_comparison.html",
        context=_base_context(request, comparison=comparison),
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> HTMLResponse:
    """Render the usable non-JavaScript job workspace page."""

    query = _workspace_query(request)
    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context=_workspace_context(request, service, query),
    )


@router.get("/jobs/results", response_class=HTMLResponse)
def job_results(
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> HTMLResponse:
    """Render a focused HTMX result-table update for the current filters."""

    query = _workspace_query(request)
    return templates.TemplateResponse(
        request=request,
        name="fragments/job_results.html",
        context=_workspace_context(request, service, query),
    )


@router.get("/exports/jobs")
def web_export_jobs(
    request: Request,
    service: Annotated[ExportService, Depends(get_export_service)],
) -> StreamingResponse:
    """Download selected jobs from the HTML workspace without a loopback API call."""

    payload: dict[str, object] = {
        name: value
        for name, value in request.query_params.items()
        if name in JobExportRequest.model_fields
    }
    payload["job_ids"] = request.query_params.getlist("job_ids")
    export_request = _validated_model(JobExportRequest, payload)
    return download_response(service.export_jobs(export_request))


@router.get("/exports/sqlite")
def web_export_sqlite_backup(
    service: Annotated[ExportService, Depends(get_export_service)],
) -> StreamingResponse:
    """Download a consistent SQLite backup through the server-rendered UI."""

    return download_response(service.export_sqlite_backup())


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(
    job_id: UUID,
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
    scoring_service: Annotated[JobScoringService, Depends(get_job_scoring_service)],
) -> HTMLResponse:
    """Render all provider-neutral job detail and its user workflow state."""

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context=_base_context(
            request, item=service.get(job_id), score=scoring_service.score_job(job_id).score
        ),
    )


@router.get("/jobs/{job_id}/workflow-panel", response_class=HTMLResponse)
def workflow_panel(
    job_id: UUID,
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> HTMLResponse:
    """Render only the detail workflow panel after an HTMX state change."""

    return templates.TemplateResponse(
        request=request,
        name="fragments/workflow_panel.html",
        context=_base_context(request, item=service.get(job_id)),
    )


@router.post("/jobs/{job_id}/workflow")
async def update_job_workflow(
    job_id: UUID,
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> Response:
    """Apply one browser workflow form with an HTMX and full-page response."""

    fields = await _form_fields(request)
    changes = _validated_model(
        JobWorkflowUpdate,
        {name: _last(fields, name) for name in JobWorkflowUpdate.model_fields if name in fields},
    )
    service.update_workflow(job_id, changes)
    return _workflow_response(request, _return_path(fields, f"/jobs/{job_id}"))


@router.post("/jobs/actions")
async def bulk_job_actions(
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> Response:
    """Apply a selected-job workflow action without rerendering the full page."""

    fields = await _form_fields(request)
    command = _validated_model(
        BulkJobWorkflowUpdate,
        {"job_ids": fields.get("job_ids", []), "action": _last(fields, "action")},
    )
    service.bulk_update_workflow(command)
    return _workflow_response(request, _return_path(fields, "/jobs"))


def _base_context(request: Request, **context: object) -> dict[str, object]:
    """Supply shared, presentation-safe application metadata to every template."""

    settings: Settings = request.app.state.settings
    return {
        "application_name": settings.app.name,
        "version": settings.app.version,
        "csrf_token": getattr(request.state, "csrf_token", ""),
        **context,
    }


def _workspace_context(
    request: Request,
    service: JobWorkspaceService,
    query: JobWorkspaceQuery,
) -> dict[str, object]:
    """Build the bounded result and query-string context used by page and fragment."""

    page = service.list(query)
    return _base_context(
        request,
        page=page,
        query=query,
        refresh_query=_query_string(query),
        previous_query=_query_string(query, max(query.offset - query.limit, 0)),
        next_query=_query_string(query, query.offset + query.limit),
    )


def _workspace_query(request: Request) -> JobWorkspaceQuery:
    """Validate only recognised query parameters before they reach a service."""

    values = {
        name: value
        for name, value in request.query_params.items()
        if name in JobWorkspaceQuery.model_fields
    }
    return _validated_model(JobWorkspaceQuery, values)


def _query_string(query: JobWorkspaceQuery, offset: int | None = None) -> str:
    """Serialise validated filters for progressive-enhancement links and HTMX."""

    values = query.model_dump(mode="json", exclude_none=True)
    if offset is not None:
        values["offset"] = offset
    return urlencode(values)


async def _form_fields(request: Request) -> Mapping[str, list[str]]:
    """Parse a small URL-encoded browser form without a multipart dependency."""

    body = await request.body()
    if len(body) > _MAX_FORM_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    try:
        return parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=120)
    except (UnicodeDecodeError, ValueError) as exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT) from exception


def _last(fields: Mapping[str, list[str]], name: str) -> str | None:
    """Return the final submitted value for a single-value browser field."""

    values = fields.get(name)
    return values[-1] if values else None


def _validated_model[ModelType: BaseModel](
    model_type: type[ModelType], payload: object
) -> ModelType:
    """Turn browser validation errors into the same safe 422 status as the API."""

    try:
        return model_type.model_validate(payload)
    except ValidationError as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exception.errors(include_url=False),
        ) from exception


def _return_path(fields: Mapping[str, list[str]], default: str) -> str:
    """Allow only local form return paths to prevent an open redirect."""

    value = _last(fields, "return_to")
    return value if value and value.startswith("/") and not value.startswith("//") else default


def _workflow_response(request: Request, return_path: str) -> Response:
    """Refresh focused HTMX regions or redirect a normal HTML form submission."""

    if request.headers.get("HX-Request") == "true":
        return Response(
            status_code=status.HTTP_204_NO_CONTENT, headers={"HX-Trigger": "jobs-updated"}
        )
    return RedirectResponse(url=return_path, status_code=status.HTTP_303_SEE_OTHER)


def _authenticated_redirect(request: Request, session_value: str) -> RedirectResponse:
    """Set minimal session/CSRF cookies and redirect after successful form login."""

    token, csrf = session_value.split(".", 1)
    settings = request.app.state.settings.authentication
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
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
    return response
