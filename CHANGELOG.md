# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added

- Milestone 1 application foundation with FastAPI, SQLite, YAML settings,
  structured logging, health checks, Docker support, and quality tooling.
- Milestone 2 provider-neutral job, provider, saved-search, and provider-run
  contracts with SQLModel repositories and application services.
- Versioned CRUD API resources, deterministic durable job deduplication, and
  explicit Alembic schema migrations.
- Warning-free test compatibility: `httpx2` for Starlette's test client and
  pytest-asyncio 1.x for Python 3.14 event-loop support.
- Milestone 3 provider platform: provider contracts and automatic discovery,
  bounded local background execution, durable manual provider runs, and
  isolated failure outcomes.
- Optional JobSpy adapter with provider-neutral result normalisation and a
  focused `jobspy` dependency extra.
- Milestone 4 search workspace with dashboard metrics, server-rendered
  dashboard/results/detail pages, HTMX fragment updates, and progressive HTML
  form fallbacks.
- Durable lazy job workflow state for bookmarks, applied status, notes, and
  bounded bulk actions, with indexed SQLite filtering and API endpoints.
- Milestone 5 low-memory exports: streaming CSV/JSON, constant-memory XLSX,
  SQLite online backup, selected-job workspace controls, and export audit API.
- Milestone 6 APScheduler integration: persisted daily/cron saved-search
  schedules, durable dispatch history, manual runs, bounded retry handling,
  and low-memory single-process scheduler configuration.
- Milestone 7 direct Pnet provider: lazy Playwright lifecycle, bounded
  pagination, local HTML parsing, classified timeout/rate-limit failures, and
  deterministic parser fixtures.
- Milestone 8 deterministic scoring: local role, skill, salary, workplace,
  experience, leadership, project-management, business-analysis, and Agile
  matching with reasons, gaps, and confidence through the API and job details.
- Milestone 9 local authentication: one-time account bootstrap, salted password
  verification, opaque expiring sessions, CSRF validation, secure production
  cookies, and bounded failed-login rate limiting.
- Opt-in SMTP, Telegram, Slack, and Teams notification adapters with explicit
  configuration and payload-free durable delivery history.
- Milestone 10 private advanced matching: consented text resume skill extraction,
  source-text disposal, deletion controls, and deterministic comparison of up to
  three current jobs.
- Milestone 11 release quality: repeatable performance harness, CSP and
  production-host hardening, safe local Compose binding, Docker health checks,
  and release/restore documentation.
- Release-quality accessibility and recovery checks: keyboard skip navigation,
  non-duplicated main landmarks, live update regions, and a SQLite backup
  restore regression test.
