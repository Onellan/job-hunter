"""Server-rendered and HTMX presentation routes for the job workspace."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, cast
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
    get_manual_search_service,
    get_provider_run_service,
    get_provider_service,
    get_resume_matching_service,
    get_schedule_service,
    get_search_service,
)
from app.core.config import Settings
from app.core.downloads import download_response
from app.core.passwords import token_digest
from app.database.repositories.auth import SqliteAuthRepository
from app.models.auth import Credentials
from app.models.errors import EntityNotFoundError, NoEnabledProviderError, ResourceConflictError
from app.models.export import JobExportRequest
from app.models.matching import JobComparisonRequest, ResumeUploadRequest
from app.models.provider import ProviderCreate, ProviderRecord, ProviderUpdate
from app.models.schedule import (
    ScheduleCreate,
    ScheduleRecord,
    ScheduleRunRecord,
    ScheduleTriggerType,
    ScheduleUpdate,
)
from app.models.search import (
    RemotePreference,
    SearchCreate,
    SearchCriteria,
    SearchRecord,
    SearchUpdate,
)
from app.models.workspace import BulkJobWorkflowUpdate, JobWorkflowUpdate, JobWorkspaceQuery
from app.scheduler.runtime import SchedulerRuntime
from app.services.authentication import AuthenticationService
from app.services.dashboard import DashboardService
from app.services.exports import ExportService
from app.services.manual_searches import ManualSearchService
from app.services.matching import ResumeMatchingService
from app.services.provider_runs import ProviderRunService
from app.services.providers import ProviderService
from app.services.schedules import ScheduleService
from app.services.scoring import JobScoringService
from app.services.searches import SearchService
from app.services.workspace import JobWorkspaceService

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_MAX_FORM_BYTES = 210_000


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    """Render the local login and one-time bootstrap form."""

    return _login_response(request, None, None)


@router.post("/login")
async def login_form(request: Request) -> Response:
    """Authenticate a browser form and issue the same session cookies as the API."""

    fields = await _form_fields(request)
    username = _last(fields, "username") or ""
    try:
        credentials = Credentials.model_validate(
            {"username": username, "password": _last(fields, "password")}
        )
    except ValidationError:
        return _login_response(
            request,
            "Check your username and password.",
            username,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    client_key = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_rate_limiter
    if not limiter.check(client_key).allowed:
        return _login_response(
            request,
            "Too many sign-in attempts. Try again later.",
            username,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
    with Session(request.app.state.engine) as session:
        service = AuthenticationService(
            SqliteAuthRepository(session),
            request.app.state.settings.authentication.session_ttl_hours,
        )
        authenticated = service.login(credentials)
    if authenticated is None:
        limiter.record_failure(client_key)
        return _login_response(
            request, "Username or password is incorrect.", username, status.HTTP_401_UNAUTHORIZED
        )
    limiter.clear(client_key)
    return _authenticated_redirect(request, authenticated.csrf_token)


@router.post("/login/bootstrap")
async def bootstrap_form(request: Request) -> Response:
    """Create the first local account from the browser login boundary."""

    fields = await _form_fields(request)
    username = _last(fields, "username") or ""
    try:
        credentials = Credentials.model_validate(
            {"username": username, "password": _last(fields, "password")}
        )
    except ValidationError:
        return _login_response(
            request,
            "Check your username and password.",
            username,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    with Session(request.app.state.engine) as session:
        try:
            AuthenticationService(
                SqliteAuthRepository(session),
                request.app.state.settings.authentication.session_ttl_hours,
            ).bootstrap(credentials)
        except ResourceConflictError:
            return _login_response(
                request,
                "An account already exists. Sign in instead.",
                username,
                status.HTTP_409_CONFLICT,
            )
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout_form(request: Request) -> RedirectResponse:
    """Invalidate the current browser session through the CSRF-protected UI route."""

    settings = request.app.state.settings.authentication
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        with Session(request.app.state.engine) as session:
            SqliteAuthRepository(session).delete_session(token_digest(token))
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie("job_hunter_csrf")
    return response


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
    try:
        profile = service.upload(
            ResumeUploadRequest.model_validate(
                {"consent": _last(fields, "consent") == "true", "content": _last(fields, "content")}
            )
        )
    except ValidationError as exception:
        return templates.TemplateResponse(
            request=request,
            name="fragments/resume_profile.html",
            context=_base_context(
                request,
                profile=None,
                feedback_kind="error",
                feedback_message=_validation_message(exception),
                request_id=request.headers.get("X-Request-ID", ""),
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return templates.TemplateResponse(
        request=request,
        name="fragments/resume_profile.html",
        context=_base_context(
            request,
            profile=profile,
            feedback_kind="success",
            feedback_message="Skills were extracted and saved locally.",
            request_id=None,
        ),
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


@router.post("/jobs/compare", response_class=HTMLResponse)
async def compare_selected_jobs(
    request: Request,
    workspace_service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
    matching_service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> HTMLResponse:
    """Compare two or three selected workspace jobs without exposing their identifiers."""

    fields = await _form_fields(request)
    try:
        comparison = matching_service.compare(
            JobComparisonRequest.model_validate({"job_ids": fields.get("job_ids", [])})
        )
    except ValidationError as exception:
        return templates.TemplateResponse(
            request=request,
            name="jobs.html",
            context=_workspace_context(
                request,
                workspace_service,
                _workspace_query(request),
                comparison_error=_validation_message(exception),
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return templates.TemplateResponse(
        request=request,
        name="matching.html",
        context=_base_context(request, profile=None, comparison=comparison, comparison_error=None),
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> Response:
    """Render the usable non-JavaScript job workspace page."""

    query = _workspace_query(request)
    if _has_blank_workspace_filters(request):
        return RedirectResponse(
            url=f"/jobs?{_query_string(query)}", status_code=status.HTTP_303_SEE_OTHER
        )
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
    response = templates.TemplateResponse(
        request=request,
        name="fragments/job_results.html",
        context=_workspace_context(request, service, query),
    )
    if _has_blank_workspace_filters(request):
        response.headers["HX-Push-Url"] = f"/jobs?{_query_string(query)}"
    return response


@router.get("/searches", response_class=HTMLResponse)
def searches_page(
    request: Request,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> HTMLResponse:
    """Render saved searches and the browser-native create form."""

    return templates.TemplateResponse(
        request=request,
        name="searches.html",
        context=_base_context(
            request,
            searches=service.list(0, 100).items,
            form_values=_search_form_values(None),
            form_error=None,
        ),
    )


@router.get("/providers", response_class=HTMLResponse)
def providers_page(
    request: Request,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> HTMLResponse:
    """Render provider registrations and a non-secret create form."""

    return _provider_page(request, service, None, None, status.HTTP_200_OK)


@router.post("/providers")
async def create_provider_form(
    request: Request,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> Response:
    """Create a browser-managed provider registration."""

    fields = await _form_fields(request)
    try:
        provider = _provider_from_form(fields)
    except (ValidationError, ValueError) as exception:
        return _provider_page(
            request,
            service,
            fields,
            _provider_validation_message(exception),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    created = service.create(provider)
    return RedirectResponse(url=f"/providers/{created.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/providers/{provider_id}", response_class=HTMLResponse)
def provider_detail_page(
    provider_id: UUID,
    request: Request,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> HTMLResponse:
    """Render one provider's editable non-secret configuration."""

    return _provider_detail_response(request, service.get(provider_id), None)


@router.post("/providers/{provider_id}")
async def update_provider_form(
    provider_id: UUID,
    request: Request,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> Response:
    """Update provider enablement and configuration through the browser."""

    fields = await _form_fields(request)
    try:
        provider = _provider_from_form(fields, require_code=False)
    except (ValidationError, ValueError) as exception:
        return _provider_detail_response(
            request,
            service.get(provider_id),
            _provider_validation_message(exception),
            _provider_form_values_from_fields(fields),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    updated = service.update(
        provider_id,
        ProviderUpdate(
            display_name=provider.display_name,
            enabled=provider.enabled,
            configuration=provider.configuration,
        ),
    )
    return RedirectResponse(url=f"/providers/{updated.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/providers/{provider_id}/delete")
async def delete_provider_form(
    provider_id: UUID,
    request: Request,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> Response:
    """Delete a provider only after an explicit browser confirmation."""

    fields = await _form_fields(request)
    provider = service.get(provider_id)
    if _last(fields, "confirm_delete") != "true":
        return _provider_detail_response(
            request,
            provider,
            "Select the confirmation checkbox before removing this provider.",
            response_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    service.delete(provider_id)
    return RedirectResponse(url="/providers", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/searches")
async def create_search_form(
    request: Request,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> Response:
    """Create a saved search from a progressively enhanced HTML form."""

    fields = await _form_fields(request)
    try:
        search = _search_from_form(fields)
    except ValidationError as exception:
        return _search_form_error_response(request, service, fields, exception)
    created = service.create(search)
    return RedirectResponse(url=f"/searches/{created.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/searches/{search_id}", response_class=HTMLResponse)
def search_detail_page(
    search_id: UUID,
    request: Request,
    search_service: Annotated[SearchService, Depends(get_search_service)],
    run_service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
    schedule_service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> HTMLResponse:
    """Render one editable saved search and its bounded provider-run history."""

    return _search_detail_response(
        request, search_service.get(search_id), run_service, schedule_service, None
    )


@router.post("/searches/{search_id}")
async def update_search_form(
    search_id: UUID,
    request: Request,
    search_service: Annotated[SearchService, Depends(get_search_service)],
    run_service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
    schedule_service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> Response:
    """Update all saved-search browser fields while keeping validation local to the form."""

    fields = await _form_fields(request)
    try:
        updated = search_service.update(
            search_id,
            SearchUpdate(**_search_from_form(fields).model_dump()),
        )
    except ValidationError as exception:
        return _search_detail_response(
            request,
            search_service.get(search_id),
            run_service,
            schedule_service,
            _validation_message(exception),
            _search_form_values_from_fields(fields),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return RedirectResponse(url=f"/searches/{updated.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/searches/{search_id}/run")
async def run_search_form(
    search_id: UUID,
    request: Request,
    search_service: Annotated[SearchService, Depends(get_search_service)],
    run_service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
    manual_service: Annotated[ManualSearchService, Depends(get_manual_search_service)],
) -> Response:
    """Queue a saved search without blocking the browser on provider execution."""

    search = search_service.get(search_id)
    try:
        started = manual_service.start(search_id)
        message = f"Queued {len(started.provider_runs)} provider run(s)."
        if started.skipped_provider_codes:
            message += (
                f" Skipped unavailable providers: {', '.join(started.skipped_provider_codes)}."
            )
    except NoEnabledProviderError:
        message = (
            "No enabled provider matches this saved search. Enable a provider before running it."
        )

    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="fragments/saved_search_runs.html",
            context=_search_detail_context(request, search, run_service, message=message),
        )
    return RedirectResponse(url=f"/searches/{search_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/searches/{search_id}/schedules")
async def create_schedule_form(
    search_id: UUID,
    request: Request,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> Response:
    """Create and register a recurring schedule from its owning saved search."""

    fields = await _form_fields(request)
    try:
        schedule = _schedule_from_form(search_id, fields)
    except ValidationError as exception:
        return _schedule_error_response(request, search_id, service, fields, exception)
    created = service.create(schedule)
    _scheduler_runtime(request).sync(created)
    return RedirectResponse(url=f"/searches/{search_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/searches/{search_id}/schedules/{schedule_id}")
async def update_schedule_form(
    search_id: UUID,
    schedule_id: UUID,
    request: Request,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> Response:
    """Update schedule controls and resynchronise the in-process trigger."""

    fields = await _form_fields(request)
    try:
        submitted = _schedule_from_form(search_id, fields)
    except ValidationError as exception:
        return _schedule_error_response(request, search_id, service, fields, exception)
    updated = service.update(
        schedule_id,
        ScheduleUpdate.model_validate(submitted.model_dump(exclude={"search_id"})),
    )
    _scheduler_runtime(request).sync(updated)
    return RedirectResponse(url=f"/searches/{search_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/searches/{search_id}/schedules/{schedule_id}/run")
async def run_schedule_form(search_id: UUID, schedule_id: UUID, request: Request) -> Response:
    """Queue an immediate schedule dispatch without blocking the browser."""

    _scheduler_runtime(request).run_now(schedule_id)
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse('<p class="status-message" role="status">Schedule run queued.</p>')
    return RedirectResponse(url=f"/searches/{search_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/searches/{search_id}/schedules/{schedule_id}/delete")
async def delete_schedule_form(
    search_id: UUID,
    schedule_id: UUID,
    request: Request,
    service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> Response:
    """Remove a schedule trigger while retaining its durable dispatch history."""

    service.delete(schedule_id)
    _scheduler_runtime(request).remove(schedule_id)
    return RedirectResponse(url=f"/searches/{search_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/provider-runs/{run_id}", response_class=HTMLResponse)
def provider_run_detail_page(
    run_id: UUID,
    request: Request,
    service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
) -> HTMLResponse:
    """Render the safe durable status for a provider run linked from saved searches."""

    return templates.TemplateResponse(
        request=request,
        name="provider_run_detail.html",
        context=_base_context(request, run=service.get(run_id)),
    )


@router.get("/runs", response_class=HTMLResponse)
def operations_page(
    request: Request,
    provider_run_service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
    schedule_service: Annotated[ScheduleService, Depends(get_schedule_service)],
) -> HTMLResponse:
    """Render bounded provider and schedule dispatch history for operations review."""

    search_id = request.query_params.get("search_id")
    provider_id = request.query_params.get("provider_id")
    status_filter = request.query_params.get("status")
    offset = _bounded_offset(request.query_params.get("offset"))
    provider_runs = provider_run_service.list(
        offset, 25, _optional_uuid(provider_id), _optional_uuid(search_id)
    )
    all_schedule_runs = _all_schedule_runs(schedule_service, search_id, status_filter)
    schedule_total = len(all_schedule_runs)
    schedule_runs = all_schedule_runs[offset : offset + 25]
    return templates.TemplateResponse(
        request=request,
        name="runs.html",
        context=_base_context(
            request,
            provider_runs=provider_runs,
            schedule_runs=schedule_runs,
            schedule_total=schedule_total,
            offset=offset,
            status_filter=status_filter or "",
            search_id=search_id or "",
            provider_id=provider_id or "",
        ),
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
        "current_user": getattr(request.state, "current_user", None),
        "active_page": _active_page(request.url.path),
        **context,
    }


def _active_page(path: str) -> str | None:
    """Map a presentation route to its primary navigation destination."""

    if path in {"/", "/dashboard"}:
        return "dashboard"
    if path.startswith("/jobs"):
        return "jobs"
    if path.startswith("/searches"):
        return "searches"
    if path.startswith("/providers"):
        return "providers"
    if path.startswith("/matching"):
        return "matching"
    if path.startswith("/runs") or path.startswith("/provider-runs"):
        return "operations"
    return None


def _login_response(
    request: Request,
    message: str | None,
    username: str | None,
    response_status: int = status.HTTP_200_OK,
) -> HTMLResponse:
    """Render safe local-auth feedback without retaining submitted passwords."""

    with Session(request.app.state.engine) as session:
        bootstrap_available = SqliteAuthRepository(session).user_count() == 0
    response = templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_base_context(
            request,
            login_message=message,
            login_username=username or "",
            bootstrap_available=bootstrap_available,
        ),
        status_code=response_status,
    )
    if response_status == status.HTTP_429_TOO_MANY_REQUESTS:
        response.headers["Retry-After"] = "60"
    return response


def _search_detail_response(
    request: Request,
    search: SearchRecord,
    run_service: ProviderRunService,
    schedule_service: ScheduleService,
    form_error: str | None,
    form_values: dict[str, object] | None = None,
    response_status: int = status.HTTP_200_OK,
) -> HTMLResponse:
    """Render an editable saved-search detail page with a safe form error."""

    return templates.TemplateResponse(
        request=request,
        name="search_detail.html",
        context=_search_detail_context(
            request,
            search,
            run_service,
            schedule_service,
            form_error=form_error,
            form_values=form_values or _search_form_values(search),
        ),
        status_code=response_status,
    )


def _search_detail_context(
    request: Request,
    search: SearchRecord,
    run_service: ProviderRunService,
    schedule_service: ScheduleService | None = None,
    **context: object,
) -> dict[str, object]:
    """Build bounded saved-search detail context without provider-specific data."""

    return _base_context(
        request,
        search=search,
        runs=run_service.list(0, 25, None, search.id),
        schedule_panels=(
            _schedule_panels(search.id, schedule_service) if schedule_service is not None else []
        ),
        schedule_form_values=_schedule_form_values(),
        schedule_form_error=None,
        **context,
    )


def _search_form_error_response(
    request: Request,
    service: SearchService,
    fields: Mapping[str, list[str]],
    exception: ValidationError,
) -> HTMLResponse:
    """Keep create-form validation feedback in the rendered saved-search page."""

    return templates.TemplateResponse(
        request=request,
        name="searches.html",
        context=_base_context(
            request,
            searches=service.list(0, 100).items,
            form_values=_search_form_values_from_fields(fields),
            form_error=_validation_message(exception),
        ),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def _search_from_form(fields: Mapping[str, list[str]]) -> SearchCreate:
    """Translate compact comma-separated HTML controls into provider-neutral criteria."""

    criteria = {
        "keywords": _csv_values(fields, "keywords"),
        "boolean_query": _last(fields, "boolean_query") or None,
        "excluded_keywords": _csv_values(fields, "excluded_keywords"),
        "locations": _csv_values(fields, "locations"),
        "remote_preference": _last(fields, "remote_preference") or RemotePreference.ANY,
        "minimum_salary": _last(fields, "minimum_salary") or None,
        "experience_levels": _csv_values(fields, "experience_levels"),
        "posted_within_days": _last(fields, "posted_within_days") or None,
        "provider_codes": _csv_values(fields, "provider_codes"),
        "included_companies": _csv_values(fields, "included_companies"),
        "excluded_companies": _csv_values(fields, "excluded_companies"),
    }
    return SearchCreate(
        name=_last(fields, "name") or "",
        enabled=_last(fields, "enabled") == "true",
        criteria=SearchCriteria.model_validate(criteria),
    )


def _csv_values(fields: Mapping[str, list[str]], name: str) -> list[str]:
    """Return trimmed comma-separated values, preserving model-level validation."""

    return [value.strip() for value in (_last(fields, name) or "").split(",") if value.strip()]


def _search_form_values(search: SearchRecord | None) -> dict[str, object]:
    """Convert durable criteria into form values without exposing internal models."""

    criteria = search.criteria if search else SearchCriteria()
    return {
        "name": search.name if search else "",
        "enabled": search.enabled if search else True,
        "keywords": ", ".join(criteria.keywords),
        "boolean_query": criteria.boolean_query or "",
        "excluded_keywords": ", ".join(criteria.excluded_keywords),
        "locations": ", ".join(criteria.locations),
        "remote_preference": criteria.remote_preference.value,
        "minimum_salary": (
            str(criteria.minimum_salary) if criteria.minimum_salary is not None else ""
        ),
        "experience_levels": ", ".join(criteria.experience_levels),
        "posted_within_days": str(criteria.posted_within_days or ""),
        "provider_codes": ", ".join(criteria.provider_codes),
        "included_companies": ", ".join(criteria.included_companies),
        "excluded_companies": ", ".join(criteria.excluded_companies),
    }


def _search_form_values_from_fields(fields: Mapping[str, list[str]]) -> dict[str, object]:
    """Retain safe browser values after a validation failure."""

    values = _search_form_values(None)
    for name in values:
        if name in fields:
            values[name] = _last(fields, name) or ""
    values["enabled"] = _last(fields, "enabled") == "true"
    return values


def _validation_message(exception: ValidationError) -> str:
    """Return one concise, presentation-safe validation message."""

    error = exception.errors(include_url=False)[0]
    location = " → ".join(str(part) for part in error["loc"])
    return f"Check {location}: {error['msg']}"


def _schedule_panels(search_id: UUID, service: ScheduleService) -> list[dict[str, object]]:
    """Return each search schedule with only its ten newest durable dispatch outcomes."""

    schedules = [item for item in service.list(0, 100).items if item.search_id == search_id]
    return [
        {
            "schedule": schedule,
            "runs": service.list_runs(schedule.id, 0, 10).items,
            "form_values": _schedule_form_values(schedule),
        }
        for schedule in schedules
    ]


def _all_schedule_runs(
    service: ScheduleService, search_id: str | None, status_filter: str | None
) -> list[ScheduleRunRecord]:
    """Return a compact newest-first operational sample across persisted schedules."""

    selected_search = _optional_uuid(search_id)
    runs = []
    for schedule in service.list(0, 100).items:
        if selected_search is not None and schedule.search_id != selected_search:
            continue
        for run in service.list_runs(schedule.id, 0, 10).items:
            if status_filter and run.status.value != status_filter:
                continue
            runs.append(run)
    return sorted(runs, key=lambda run: run.created_at, reverse=True)


def _bounded_offset(value: str | None) -> int:
    """Parse a bounded non-negative offset for compact operations pagination."""

    try:
        offset = int(value or "0")
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT) from exception
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    return offset


def _optional_uuid(value: str | None) -> UUID | None:
    """Validate an optional UUID query value before using it in a service call."""

    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT) from exception


def _schedule_from_form(search_id: UUID, fields: Mapping[str, list[str]]) -> ScheduleCreate:
    """Translate the compact daily or cron browser controls into a schedule contract."""

    trigger_type = _last(fields, "trigger_type") or ""
    payload = {
        "name": _last(fields, "name") or "",
        "search_id": search_id,
        "trigger_type": trigger_type,
        "daily_time": _last(fields, "daily_time") or None,
        "cron_expression": _last(fields, "cron_expression") or None,
        "enabled": _last(fields, "enabled") == "true",
        "incremental": _last(fields, "incremental") == "true",
        "retry_limit": _last(fields, "retry_limit") or 1,
    }
    return ScheduleCreate.model_validate(payload)


def _schedule_error_response(
    request: Request,
    search_id: UUID,
    service: ScheduleService,
    fields: Mapping[str, list[str]],
    exception: ValidationError,
) -> HTMLResponse:
    """Return local schedule-form feedback without raw API validation output."""

    return templates.TemplateResponse(
        request=request,
        name="fragments/schedule_form_feedback.html",
        context=_base_context(
            request,
            schedule_form_values=_schedule_form_values_from_fields(fields),
            schedule_form_error=_validation_message(exception),
            search_id=search_id,
            schedule_panels=_schedule_panels(search_id, service),
        ),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def _schedule_form_values_from_fields(fields: Mapping[str, list[str]]) -> dict[str, object]:
    """Preserve valid-looking schedule controls after local validation feedback."""

    return {
        "name": _last(fields, "name") or "",
        "trigger_type": _last(fields, "trigger_type") or ScheduleTriggerType.DAILY.value,
        "daily_time": _last(fields, "daily_time") or "",
        "cron_expression": _last(fields, "cron_expression") or "",
        "enabled": _last(fields, "enabled") == "true",
        "incremental": _last(fields, "incremental") == "true",
        "retry_limit": _last(fields, "retry_limit") or "1",
    }


def _schedule_form_values(schedule: ScheduleRecord | None = None) -> dict[str, object]:
    """Convert a durable schedule into controlled browser values."""

    if schedule is None:
        return {
            "name": "",
            "trigger_type": ScheduleTriggerType.DAILY.value,
            "daily_time": "08:00",
            "cron_expression": "",
            "enabled": True,
            "incremental": True,
            "retry_limit": "1",
        }
    return {
        "name": schedule.name,
        "trigger_type": schedule.trigger_type.value,
        "daily_time": schedule.daily_time.strftime("%H:%M") if schedule.daily_time else "",
        "cron_expression": schedule.cron_expression or "",
        "enabled": schedule.enabled,
        "incremental": schedule.incremental,
        "retry_limit": str(schedule.retry_limit),
    }


def _scheduler_runtime(request: Request) -> SchedulerRuntime:
    """Return the composed scheduler adapter without importing it into the domain layer."""

    return cast(SchedulerRuntime, request.app.state.scheduler)


def _provider_page(
    request: Request,
    service: ProviderService,
    fields: Mapping[str, list[str]] | None,
    form_error: str | None,
    response_status: int,
) -> HTMLResponse:
    """Render the provider list with local validation feedback."""

    return templates.TemplateResponse(
        request=request,
        name="providers.html",
        context=_base_context(
            request,
            providers=service.list(0, 100).items,
            form_values=(
                _provider_form_values_from_fields(fields)
                if fields is not None
                else _provider_form_values(None)
            ),
            form_error=form_error,
        ),
        status_code=response_status,
    )


def _provider_detail_response(
    request: Request,
    provider: ProviderRecord,
    form_error: str | None,
    form_values: dict[str, object] | None = None,
    response_status: int = status.HTTP_200_OK,
) -> HTMLResponse:
    """Render one provider configuration without exposing unsafe form data."""

    return templates.TemplateResponse(
        request=request,
        name="provider_detail.html",
        context=_base_context(
            request,
            provider=provider,
            form_error=form_error,
            form_values=form_values or _provider_form_values(provider),
        ),
        status_code=response_status,
    )


def _provider_from_form(
    fields: Mapping[str, list[str]], *, require_code: bool = True
) -> ProviderCreate:
    """Validate compact non-secret provider controls from a browser form."""

    configuration = _provider_configuration(_last(fields, "configuration"))
    payload: dict[str, object] = {
        "code": _last(fields, "code") or ("temporary" if not require_code else ""),
        "display_name": _last(fields, "display_name") or "",
        "enabled": _last(fields, "enabled") == "true",
        "configuration": configuration,
    }
    return ProviderCreate.model_validate(payload)


def _provider_configuration(value: str | None) -> dict[str, object]:
    """Parse a JSON object and reject credential-like configuration keys."""

    if not value or not value.strip():
        return {}
    if len(value) > 10_000:
        raise ValueError("Configuration must be 10,000 characters or fewer.")
    try:
        configuration = json.loads(value)
    except json.JSONDecodeError as exception:
        raise ValueError("Configuration must be a valid JSON object.") from exception
    if not isinstance(configuration, dict):
        raise ValueError("Configuration must be a JSON object.")
    if _contains_sensitive_configuration_key(configuration):
        raise ValueError("Provider credentials must be configured outside the browser form.")
    return configuration


def _contains_sensitive_configuration_key(value: object) -> bool:
    """Identify credential-like keys recursively without retaining their values."""

    sensitive_parts = (
        "password",
        "token",
        "secret",
        "apikey",
        "authorization",
        "cookie",
        "credential",
        "privatekey",
        "bearer",
        "session",
        "headers",
    )
    if isinstance(value, dict):
        return any(
            any(
                part
                in "".join(character for character in str(key).casefold() if character.isalnum())
                for part in sensitive_parts
            )
            or _contains_sensitive_configuration_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_configuration_key(child) for child in value)
    return False


def _provider_form_values(provider: ProviderRecord | None) -> dict[str, object]:
    """Return safe editable provider values for a browser form."""

    return {
        "code": provider.code if provider else "",
        "display_name": provider.display_name if provider else "",
        "enabled": provider.enabled if provider else True,
        "configuration": (
            json.dumps(provider.configuration, indent=2, sort_keys=True)
            if provider and not _contains_sensitive_configuration_key(provider.configuration)
            else "{}"
        ),
    }


def _provider_form_values_from_fields(fields: Mapping[str, list[str]]) -> dict[str, object]:
    """Preserve non-sensitive browser values when a provider form is invalid."""

    return {
        "code": _last(fields, "code") or "",
        "display_name": _last(fields, "display_name") or "",
        "enabled": _last(fields, "enabled") == "true",
        "configuration": "{}",
    }


def _provider_validation_message(exception: ValidationError | ValueError) -> str:
    """Keep provider configuration feedback concise and free of submitted payloads."""

    if isinstance(exception, ValidationError):
        return _validation_message(exception)
    return str(exception)


def _workspace_context(
    request: Request,
    service: JobWorkspaceService,
    query: JobWorkspaceQuery,
    **context: object,
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
        **context,
    )


def _workspace_query(request: Request) -> JobWorkspaceQuery:
    """Validate only recognised query parameters before they reach a service."""

    values = {
        name: value
        for name, value in request.query_params.items()
        if name in JobWorkspaceQuery.model_fields and value.strip()
    }
    return _validated_model(JobWorkspaceQuery, values)


def _has_blank_workspace_filters(request: Request) -> bool:
    """Identify browser-submitted empty optional filters that should be omitted from URLs."""

    return any(
        name in JobWorkspaceQuery.model_fields and not value.strip()
        for name, value in request.query_params.items()
    )


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
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
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
