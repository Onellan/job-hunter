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

## Milestone 3 — Provider Platform

- [ ] Add `BaseProvider`, provider registry/discovery, enablement configuration,
      bounded local execution, and isolated provider-run outcomes.
- [ ] Add the JobSpy adapter behind the standard contract.
- [ ] Add manual search execution and deterministic fake-provider tests.

## Milestone 4 — Search Workspace

- [ ] Build dashboard metrics, provider/error status, and recent searches.
- [ ] Build server-rendered search, filter, result, pagination, and job-detail
      pages with focused HTMX updates.
- [ ] Add bookmarks, applied state, notes, bulk actions, and accessible fallbacks.

## Milestone 5 — Export

- [ ] Stream CSV and JSON exports.
- [ ] Add constant-memory XLSX export and SQLite backup export.
- [ ] Support selected-job export, audit events, API endpoints, and UI controls.

## Milestone 6 — Scheduler

- [ ] Add APScheduler daily and cron schedules, persisted run history, manual
      runs, bounded retries, and incremental-search behaviour.

## Milestone 7 — Direct Providers

- [ ] Add the Pnet Playwright adapter with explicit browser lifecycle,
      pagination, parser fixtures, rate limits, retry classification, and
      low-concurrency safeguards.

## Milestone 8 — Explainable Scoring

- [ ] Add deterministic role, skill, salary, remote, leadership, experience,
      project-management, business-analysis, and Agile scoring.
- [ ] Show reasons, matches, gaps, and confidence; make external AI opt-in.

## Milestone 9 — Authentication and Notifications

- [ ] Add password hashing, sessions, CSRF, authorization, secure defaults, and
      rate limits before exposing state-changing browser workflows.
- [ ] Add opt-in notification adapters (email, Telegram, Teams, Slack) with
      safe configuration and delivery history.

## Milestone 10 — Advanced Matching

- [ ] Add consented resume upload, skill extraction, and job comparison.

## Milestone 11 — Release Quality

- [ ] Profile memory and latency on target-class hardware.
- [ ] Complete accessibility, security, documentation, backup/restore, and
      deployment checks.
- [ ] Prepare release notes and a reproducible release checklist.
