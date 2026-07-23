# Job-Hunter Roadmap

## Milestone 1 — Foundation ✅

- [x] Create the prescribed project structure.
- [x] Configure FastAPI application factory, Jinja2 landing page, static assets,
      structured logging, request IDs, and security headers.
- [x] Configure YAML/Pydantic settings with environment overrides.
- [x] Configure SQLite/SQLModel engine lifecycle and health endpoint.
- [x] Add Dockerfile, Docker Compose, non-root container, and CLI entry point.
- [x] Add tests, Ruff, Black, isort, mypy, pytest, pytest-asyncio, and
      pre-commit configuration.
- [x] Add architecture, configuration, deployment, contribution, and changelog
      documentation.

## Milestone 2 — Domain and Persistence ✅

- [x] Define provider-neutral job, search, provider, and provider-run contracts.
- [x] Add SQLModel table mappings and an Alembic migration workflow for the
      first durable schema; production never relies on implicit schema creation.
- [x] Implement repository protocols, SQLite implementations, and application
      services that preserve architectural boundaries.
- [x] Add deterministic, database-backed job identity and idempotent
      deduplication using stable ID, canonical URL, then fingerprint.
- [x] Add indexes for identity, source, date, workplace filtering, and run
      history paths.
- [x] Expose tested paginated CRUD JSON resources for jobs, searches, providers,
      and provider runs with lifecycle validation.
- [x] Document the data model, API contracts, migration operations, and current
      retention/privacy choices.

## Milestone 3 — Provider Platform ✅

- [x] Add `BaseProvider`, provider registry/discovery, enablement configuration,
      bounded local execution, and isolated provider-run outcomes.
- [x] Add the JobSpy adapter behind the standard contract.
- [x] Add manual search execution and deterministic fake-provider tests.

## Milestone 4 — Search Workspace ✅

- [x] Build dashboard metrics, provider/error status, and recent searches.
- [x] Build server-rendered search, filter, result, pagination, and job-detail
      pages with focused HTMX updates.
- [x] Add bookmarks, applied state, notes, bulk actions, and accessible fallbacks.

## Milestone 5 — Export ✅

- [x] Stream CSV and JSON exports.
- [x] Add constant-memory XLSX export and SQLite backup export.
- [x] Support selected-job export, audit events, API endpoints, and UI controls.

## Milestone 6 — Scheduler ✅

- [x] Add APScheduler daily and cron schedules, persisted run history, manual
      runs, bounded retries, and incremental-search behaviour.

## Milestone 7 — Direct Providers ✅

- [x] Add the Pnet Playwright adapter with explicit browser lifecycle,
      pagination, parser fixtures, rate limits, retry classification, and
      low-concurrency safeguards.

## Milestone 8 — Explainable Scoring ✅

- [x] Add deterministic role, skill, salary, remote, leadership, experience,
      project-management, business-analysis, and Agile scoring.
- [x] Show reasons, matches, gaps, and confidence; make external AI opt-in.

## Milestone 9 — Authentication and Notifications

- [x] Add password hashing, sessions, CSRF, authorization, secure defaults, and
      rate limits before exposing state-changing browser workflows.
- [x] Add opt-in notification adapters (email, Telegram, Teams, Slack) with
      safe configuration and delivery history.

## Milestone 10 — Advanced Matching

- [x] Add consented resume upload, skill extraction, and job comparison.

## Milestone 11 — Release Quality

- [ ] Profile memory and latency on target-class hardware (benchmark harness
      and non-target baseline are available; Raspberry Pi evidence is pending).
- [x] Complete accessibility, security, documentation, backup/restore, and
      deployment checks (automated restore and accessibility checks are in
      place; Docker and the manual browser accessibility audit completed on
      2026-07-23; target-device evidence remains separately pending).
- [x] Prepare release notes and a reproducible release checklist.

## UI Review Backlog — 2026-07-23

### UI-001: Prevent blank job filters from producing a raw validation error

- **Priority:** P0
- **Area:** `/jobs`, `/jobs/results`, `job-filters`
- **Problem:** Runtime review confirmed that submitting the untouched filter form sends empty `text`, `source`, and `workplace_type` values; the route returns a 422 JSON document and replaces the workspace.
- **Change:** Omit empty optional query values before the HTMX/full-page request and render a local, accessible validation state for genuinely invalid filters.
- **Acceptance criteria:**
  - [x] An untouched Apply filters submission remains on a usable `/jobs` view and returns the empty-result state, never raw JSON.
  - [x] Empty source, text, and workplace values are absent from the generated request URL.
- **Tests:**
  - [x] Route regression tests cover untouched filter submissions with and without HTMX.
- **Effort:** S
- **Pi impact:** None
- **Source:** Runtime review

### UI-002: Make the CSP compatible with HTMX interactions

- **Priority:** P0
- **Area:** Global security headers and HTMX fragments
- **Problem:** Every reviewed browser route logs a CSP violation because HTMX attempts to apply inline indicator styling; this undermines focused updates and leaves a persistent console error.
- **Change:** Use a narrowly scoped CSP-compatible HTMX configuration or remove the blocked behavior without weakening the policy; keep third-party asset origins explicitly allow-listed.
- **Acceptance criteria:**
  - [x] Dashboard, Jobs, Matching, and HTMX GET/POST interactions complete with zero CSP console errors.
  - [x] The final policy still blocks arbitrary inline scripts and object embedding.
- **Tests:**
  - [x] Browser console smoke test covers one HTMX GET and one HTMX POST.
- **Effort:** M
- **Pi impact:** None
- **Source:** Runtime review

### UI-003: Add the saved-search creation and run workflow

- **Priority:** P1
- **Area:** New `/searches` and saved-search detail routes
- **Problem:** Saved-search CRUD and manual execution exist only under `/api/v1/searches`; a browser user cannot define the core search that drives collection.
- **Change:** Add server-rendered list, create/edit, detail, and Run now controls using the existing services, with full-page form fallbacks and focused run-status updates.
- **Acceptance criteria:**
  - [x] A user can create, edit, enable/disable, and manually run a saved search without calling the API directly.
  - [x] The detail view links each queued provider run and shows empty, queued, succeeded, and failed states.
- **Tests:**
  - [x] Endpoint/template tests cover create, validation failure, run request, and no-enabled-provider feedback.
- **Effort:** L
- **Pi impact:** Low
- **Source:** Code review / Product vision

### UI-004: Expose provider management in the browser

- **Priority:** P1
- **Area:** New `/providers` route and operations navigation
- **Problem:** Provider CRUD, enablement, and safe error records are API-only, leaving the browser workflow unable to configure a source before running a search.
- **Change:** Add a compact providers list/create/edit/enable UI that uses existing provider contracts and displays safe dependency/configuration errors.
- **Acceptance criteria:**
  - [x] Users can add, enable, disable, edit, and remove a provider through browser forms with confirmation for deletion.
  - [x] Provider configuration validation errors remain on the form and never expose credentials or raw provider payloads.
- **Tests:**
  - [x] Endpoint/template tests cover enablement, invalid configuration, and deletion confirmation.
- **Effort:** M
- **Pi impact:** Low
- **Source:** Code review / Product vision

### UI-005: Add saved-search schedules and dispatch history to the UI

- **Priority:** P1
- **Area:** Saved-search detail schedule section
- **Problem:** Schedules, manual dispatch, retry state, and run history are API-only, so recurring collection cannot be managed from the web application.
- **Change:** Add daily/cron schedule forms and a bounded recent dispatch-history fragment beneath the owning saved search.
- **Acceptance criteria:**
  - [x] A user can create, edit, enable/disable, run, and delete a schedule from its saved-search detail page.
  - [x] The page shows the latest 10 dispatch outcomes with safe status/error details and provider-run links.
- **Tests:**
  - [x] Endpoint/template tests cover valid daily forms, invalid cron feedback, and schedule lifecycle controls.
- **Effort:** L
- **Pi impact:** Low
- **Source:** Code review / Product vision

### UI-006: Add an operations view for provider and schedule failures

- **Priority:** P1
- **Area:** New `/runs` route and dashboard error CTA
- **Problem:** The dashboard reports error counts, but provider-run and schedule-run details are API-only; users cannot diagnose or retry collection failures from the UI.
- **Change:** Add a paginated operations page with status/provider/search filters and links from dashboard errors to durable run details.
- **Acceptance criteria:**
  - [x] Users can view bounded provider and schedule run history, status, counts, timestamps, and safe error details.
  - [x] Dashboard error and last-run content link to the relevant operations view.
- **Tests:**
  - [x] Endpoint/template tests cover empty, failed, and paginated run histories.
- **Effort:** M
- **Pi impact:** Low
- **Source:** Code review / Product vision

### UI-007: Remove horizontal overflow from mobile navigation and matching

- **Priority:** P1
- **Area:** Global header and `/matching` at 390 × 844
- **Problem:** Runtime review at 390 × 844 showed a page-level horizontal scrollbar and clipped header navigation on the matching page.
- **Change:** Make navigation wrap, collapse, or use an accessible lightweight menu at narrow widths; ensure matching cards and forms fit the viewport without global horizontal scrolling.
- **Acceptance criteria:**
  - [x] At 390 × 844, `/dashboard`, `/jobs`, `/matching`, and `/login` have no document-level horizontal overflow.
  - [x] All primary navigation destinations remain visible or reachable by keyboard and touch at 390 px.
- **Tests:**
  - [x] Browser viewport regression checks cover 390 × 844, 768 × 1024, and 1366 × 768.
- **Effort:** M
- **Pi impact:** None
- **Source:** Runtime review

### UI-008: Complete account/session affordances and login feedback

- **Priority:** P1
- **Area:** Base navigation, `/login`, authenticated forms
- **Problem:** The UI has no logout/account control, always displays first-time setup, and returns generic HTTP errors instead of accessible feedback for invalid credentials or rate limits.
- **Change:** Show the signed-in account and logout control when authenticated, hide bootstrap after an owner exists, and render safe inline login/validation/rate-limit feedback.
- **Acceptance criteria:**
  - [x] An authenticated user can log out from every browser page and is redirected to the login screen.
  - [x] Login, bootstrap, and rate-limit errors remain on the form with an announced message and preserve non-sensitive input.
- **Tests:**
  - [x] Authenticated browser-route tests cover logout, invalid login, rate limit, and post-bootstrap login rendering.
- **Effort:** M
- **Pi impact:** None
- **Source:** Code review / Runtime review

### UI-009: Replace manual job UUID comparison with selected-job controls

- **Priority:** P2
- **Area:** `/jobs` selection form and `/matching`
- **Problem:** Resume matching requires users to copy and paste two or three opaque job UUIDs, making comparison effectively undiscoverable.
- **Change:** Add a Compare selected action to the existing job selection form and render the comparison with a full-page fallback.
- **Acceptance criteria:**
  - [x] Selecting two or three jobs enables a comparison action without exposing UUID entry.
  - [x] Selecting fewer than two or more than three jobs yields a clear local validation message.
- **Tests:**
  - [x] Route and template tests cover selection limits and the non-JavaScript fallback.
- **Effort:** S
- **Pi impact:** None
- **Source:** Runtime review / Code review

### UI-010: Surface the required job-search filters and reset control

- **Priority:** P2
- **Area:** `/jobs` filter panel
- **Problem:** The current UI exposes text, source, workplace, bookmark/applied, and sort only; location, date posted, salary, employment type, company include/exclude, keyword exclusions, and a reset action from the product vision are absent.
- **Change:** Extend the validated workspace query and filter panel incrementally, starting with location, employment type, date posted, and reset; add the remaining criteria only where durable data supports them.
- **Acceptance criteria:**
  - [x] Each exposed filter changes the bounded SQLite query and is preserved in pagination URLs.
  - [x] Reset restores the default workspace without a page error or stale HTMX state.
- **Tests:**
  - [x] API and template tests cover each released filter, reset, and persisted query controls.
- **Effort:** L
- **Pi impact:** Low
- **Source:** Product vision / Code review

### UI-011: Provide consistent browser success, empty, validation, and server-error states

- **Priority:** P2
- **Area:** Forms and HTMX targets across dashboard, jobs, matching, and future operations pages
- **Problem:** The reviewed blank filter failure exposes raw API validation JSON, and most browser forms have no visible success, retry, or server-error feedback region.
- **Change:** Introduce small reusable server-rendered feedback fragments with ARIA live announcements and safe correlation IDs for unexpected errors.
- **Acceptance criteria:**
  - [x] State-changing matching forms announce visible success or validation feedback without developer tools.
  - [x] Presentation-route validation and unexpected failures render safe HTML rather than raw JSON.
- **Tests:**
  - [x] Route/template tests cover matching success and 422 HTML feedback; generic browser 4xx/5xx handling is covered by the shared adapter.
- **Effort:** M
- **Pi impact:** None
- **Source:** Runtime review

### UI-012: Add navigation context and safe audit-history access

- **Priority:** P3
- **Area:** Base navigation, exports, notifications
- **Problem:** The navigation has no active-page state, while export audit events and notification delivery history are backend-only despite being useful operational feedback.
- **Change:** Add active navigation semantics and compact, paginated history links from the relevant workspace/settings surfaces without exposing notification secrets.
- **Acceptance criteria:**
  - [x] The current route is announced with `aria-current="page"` in primary navigation.
  - [x] Users can view bounded export and notification outcomes containing only safe metadata.
- **Tests:**
  - [x] Template tests cover active navigation and history empty/populated states.
- **Effort:** M
- **Pi impact:** Low
- **Source:** Code review / Runtime review
