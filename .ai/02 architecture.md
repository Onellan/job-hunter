# Job-Hunter Architecture

## Architectural intent

Job-Hunter is a modular monolith: one deployable FastAPI process, one local
SQLite database by default, and no distributed infrastructure. It is API-first
without forcing the server-rendered UI to issue wasteful loopback HTTP calls.
Both JSON endpoints and Jinja2/HTMX routes call the same application services
and use the same validated contracts.

```text
Browser or API client
        │
api/ and routers/              Presentation adapters
        │
services/                      Application use cases
        │
models/                        Provider-neutral domain contracts
   ┌────┼─────────┬──────────┐
database/   providers/   exporters/   scheduler/   Infrastructure adapters
```

Only inward imports are permitted. Infrastructure may implement an interface
defined inward; domain models do not import FastAPI, SQLModel, Playwright, or a
specific provider.

## Repository layout

| Location | Responsibility | Must not contain |
|---|---|---|
| `app/api/` | Versioned JSON endpoint adapters and response contracts | business rules or SQL |
| `app/routers/` | HTML and HTMX endpoint adapters | provider/database calls |
| `app/templates/` and `app/static/` | Presentation assets | business decisions or data access |
| `app/services/` | Search, orchestration, scoring, export, and workflow use cases | HTTP/HTML details |
| `app/models/` | Provider-neutral entities, value objects, and request/result DTOs | infrastructure imports |
| `app/database/` | SQLModel table mappings, sessions, migrations, repository implementations | provider logic |
| `app/providers/` | Provider contract, discovery, acquisition, parsing, normalisation | persistence/UI/export imports |
| `app/exporters/` | Format writers that consume service/repository data | provider calls |
| `app/scheduler/` | APScheduler registration and schedule execution adapters | duplicate search logic |
| `app/core/` | Configuration, errors, logging, middleware, security primitives | feature-specific rules |

`app/main.py` is the composition root. It wires concrete infrastructure into
the application at startup; it is the only normal place where outer layers are
assembled together.

## Standard job contract

Providers do not leak source-specific models. The domain job contract created
in Milestone 2 will represent, at minimum:

- source and stable source identifier/URL
- title, company, location, remote status, and employment type
- description and normalised salary information when available
- publication/discovery timestamps and canonical source metadata

Optional provider data remains optional. Do not invent values to satisfy a
source-specific field. Preserve raw provider payload only when necessary for
debugging and only after reviewing privacy, retention, and storage cost.

### Deduplication

Deduplication is a service concern backed by a database uniqueness strategy:

1. Prefer a source plus stable source identifier.
2. Otherwise use a canonical URL.
3. Finally use a normalised deterministic fingerprint of durable job fields.

The service is idempotent: re-running a search updates the known job's
discovery metadata rather than creating a duplicate. The database, not an
in-memory set, is the final arbiter across restarts.

## Provider architecture

Each source implements `BaseProvider` and returns only the standard job
candidate contract. Provider discovery must allow a provider package/class to
be added without edits to search services or database code.

```text
SearchService
   │
ProviderRegistry → enabled BaseProvider implementations
   │                      │
ProviderRun result ← normalised job candidates or isolated failures
```

- Provider configuration selects enabled sources; it does not contain code.
- JobSpy and other synchronous libraries run in a bounded worker thread so the
  ASGI event loop remains responsive.
- Playwright providers run asynchronously with explicit timeouts and cleanup.
- One provider failure becomes a recorded provider-run failure; successful
  providers continue.
- Retries apply only to classified transient failures, use capped exponential
  backoff with jitter, and honour provider rate limits.
- Provider tests use recorded fixtures or mocked transport, never live portals.

## Persistence

SQLite is the initial durable store. SQLModel/SQLAlchemy repository
implementations hide the database from services and providers. When the first
persistent tables are introduced, add a migration workflow rather than relying
on implicit schema creation in production.

Expected durable concepts include jobs, sources/providers, searches, provider
runs, saved searches, job state (bookmark/applied), notes, and schedules. Add
them only when their use case is implemented.

Rules:

- A service owns transaction boundaries; a provider call never runs inside one.
- Index fields used for job identity, source, publication date, filters, and
  sort order before adding memory-based filtering.
- Use offset pagination only for modest local result sets. Introduce keyset
  pagination when profiling demonstrates the need.
- Keep SQLite writes short and batch inserts/updates per completed provider
  run. Enable PostgreSQL by changing infrastructure configuration, not services.

## API and UI

JSON resources live below `/api/v1`. Request validation belongs in Pydantic
contracts; services return explicit result objects instead of framework
responses. HTML routes render full pages; HTMX endpoints return focused
fragments for filters, results, dashboard widgets, and status changes.

Progressive enhancement is required: a usable full-page route exists for every
important HTMX interaction. Prefer semantic HTML, accessible labels, keyboard
operation, and PicoCSS system dark/light theme support. Vanilla JavaScript is
permitted only when HTMX and native browser behaviour cannot fulfil the need.

## Scheduling and background work

APScheduler is an in-process adapter, not a second application. It invokes the
same search service as a manual run and records durable run history. Scheduling
must remain disabled until its milestone and configuration are present.

Long-running provider work is represented by a durable run record and executed
with bounded local concurrency. The UI polls or receives HTMX refreshes of run
status; it never blocks waiting for scraping to finish.

## Exports and scoring

Exporters consume repository/service iterators. CSV and JSON are streamed;
XLSX uses a constant-memory writer configuration. Exporting selected jobs must
not first materialise the entire matching collection.

The first scoring engine is deterministic and explainable. It returns a score,
matched skills, gaps, reasons, and confidence. Any external model is optional,
explicitly configured, fails safely, and must not receive private data without
user consent.

## Observability, resilience, and security

Use structured events such as `provider_run_completed` and
`http_request_completed`, with IDs, component, outcome, count, and duration.
Health checks remain cheap and never expose configuration or credentials.

Expected failures (timeouts, source markup changes, rate limits, unavailable
database) are handled at the boundary, logged with safe context, and surfaced
as user-visible status. Programming errors are not swallowed.

Trust boundaries are browser input, configuration/environment, provider data,
and downloaded/exported files. Validate at each boundary; use secure response
headers now and CSRF/session/rate-limit controls when authenticated
state-changing routes are added.

## Tests and extension points

Test each boundary in isolation and test user-visible use cases through FastAPI
endpoints. Fakes implement provider/repository contracts; fixture data is small
and deterministic. Add contract tests for every provider and exporter.

New providers, exporters, scoring engines, and notifiers are adapters behind
small contracts. Register/discover them through their dedicated registry, not
by adding conditionals throughout services.
