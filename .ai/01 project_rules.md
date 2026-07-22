# Job-Hunter Project Rules

## Purpose and priority

Job-Hunter is a self-hosted job aggregation platform that must run comfortably
on a Raspberry Pi 4 Model B with 1 GB RAM. These rules are authoritative for
project work. When requirements conflict, use this order:

1. Security, data integrity, and legal/provider constraints
2. Correctness and a working, tested milestone
3. Low memory, low CPU, and predictable operations
4. Maintainability and clear architecture
5. Feature breadth and convenience

Do not add complexity merely to anticipate a hypothetical scale problem.

## Delivery rules

- Work on one approved milestone at a time; leave the application runnable at
  the end of every milestone.
- Each milestone includes code, tests, user-facing documentation, a changelog
  entry, and an updated `.ai/07 todo.md`.
- Inspect existing code and documentation before creating a replacement.
- Do not introduce placeholder production code. A clearly labelled future
  extension point is acceptable only when it has no active runtime behaviour.
- Explain non-trivial architecture or dependency decisions in the final handoff.
- Preserve unrelated worktree changes. Never reset, overwrite, or delete them.

## Required technology

| Area | Standard |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| Persistence | SQLModel/SQLAlchemy 2.x; SQLite first, PostgreSQL-capable design |
| UI | Jinja2, HTMX, PicoCSS, minimal vanilla JavaScript |
| Providers | Playwright, JobSpy, BeautifulSoup, lxml when each is justified |
| Scheduling | APScheduler in the single application deployment |
| Quality | pytest, pytest-asyncio, Ruff, Black, isort, mypy, pre-commit |
| Deployment | Docker and Docker Compose; optional Nginx TLS proxy |

Never use React, Angular, Vue, Next.js, Nuxt, Svelte, Redis, RabbitMQ, Celery,
Node build systems, Webpack, Vite, microservices, Kubernetes, or a heavy
JavaScript framework.

## Architecture boundaries

Dependencies point inward:

```text
presentation (api, routers, templates)
            -> application services
            -> domain contracts (models)
infrastructure (database, providers, exporters, scheduler) -> domain contracts
```

- Routes validate and translate HTTP only. They contain no business decisions,
  scraping, or SQL.
- Services coordinate use cases and depend on contracts, not provider or
  database implementations.
- Providers return only standard job data. They never access persistence, UI,
  exporters, schedulers, or notification code.
- Repositories are the sole persistence boundary. Templates never query data.
- JSON API and HTML/HTMX routes use the same service operations and DTOs. The
  server must not make HTTP calls to itself.
- Avoid circular imports. If one appears, introduce a contract or move shared
  data inward rather than bypassing the boundary.

## Resource and runtime rules

- Keep the base installation free of browser, provider, scheduler, and export
  dependencies until their feature is enabled.
- The idle application target is under 100 MB RAM. Measure before claiming a
  target is met on Raspberry Pi hardware or an equivalent ARM environment.
- Pagination, indexed filtering, streaming downloads, and lazy job details are
  defaults—not later optimisations.
- Never run browser automation in an HTTP request handler. Provider runs use a
  bounded local executor and persist their run status.
- Default future provider concurrency is one. Raise it only after measuring
  memory, CPU, provider limits, and SQLite contention.
- A Playwright provider must reuse one short-lived browser per run, close it in
  `finally`, and never launch one browser per job page.
- Run one scheduler instance per SQLite database. Scheduler tasks call services
  and must not scrape while holding a database transaction open.
- Do not add a cache until profiling shows repeated work that SQLite indexes or
  a simpler query cannot solve.

## Configuration, security, and operations

- `config/config.yaml` is the validated baseline. Environment variables with
  the `JOB_HUNTER_` prefix override nested values. Use
  `JOB_HUNTER_CONFIG_FILE` for a deployment-specific file.
- Do not commit secrets, tokens, browser profiles, resumes, or provider
  credentials. Do not log them either.
- Validate all external input and treat provider content as untrusted.
- Use parameterised repository queries and escape user-controlled template data.
- State-changing browser routes require CSRF protection when authentication is
  introduced. Add rate limits and secure session settings with that milestone.
- Emit structured events with a request or run identifier, duration, component,
  and outcome. Avoid personal data and complete job descriptions in logs.

## Completion gate

Before handoff, run the relevant checks:

```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m isort --check-only .
python -m mypy app
```

Also run a focused behaviour check (for example, endpoint, provider fixture,
export, or scheduler test) and `git diff --check`. Report any unrun check and
why it could not be run.
