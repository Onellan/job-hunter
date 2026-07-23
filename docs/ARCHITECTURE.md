# Architecture

Job-Hunter uses a pragmatic Clean Architecture. Dependencies point inward:

```text
Presentation (app/api, app/routers, templates)
                  ↓
Application services (app/services)
                  ↓
Domain contracts (app/models)
                  ↑
Infrastructure (database, providers, exporters, scheduler)
```

## Boundaries

- **Presentation** converts HTTP requests into validated service calls. API and
  HTML/HTMX routes contain no business logic or SQL.
- **Services** coordinate the workflow and depend on repository and provider
  interfaces, never on a concrete portal or template.
- **Models** define provider-neutral domain data and request/response schemas.
- **Providers** return standard job data only; they never access SQLite or UI
  code.
- **Database** owns SQLModel tables, sessions, migrations, and repository
  implementations. Providers never write to it directly.

The JSON REST API is the stable feature contract. The server-rendered UI uses
the same services and validation contracts instead of making inefficient HTTP
calls back into the same process. A mobile client can therefore use the JSON
API without a backend redesign.

## Project layout

```text
app/
├── api/          JSON API adapters
├── core/         settings, logging, middleware, errors
├── database/     engine, migrations, tables, and repositories
├── exporters/    future export adapters
├── models/       provider-neutral contracts and state rules
├── providers/    plugin contract, discovery, adapters, and bounded execution
├── routers/      HTML and HTMX adapters
├── scheduler/    future APScheduler integration
├── services/     application workflows and persistence ports
├── static/       small CSS, JavaScript, and icon assets
├── templates/    Jinja2 templates
└── main.py       application factory
```

## Resource constraints

The application runs in one Uvicorn process and starts without opening a
database connection. The normal runtime includes the discovered JobSpy and
Pnet provider dependencies plus spreadsheet export support. Playwright starts
no browser at application startup; Docker bakes Chromium into the image and
bare-metal startup only checks its local executable path. This keeps idle
resource use small while making the built-in providers deployable by default.

SQLite is accessed through SQLModel/SQLAlchemy. The connection URL is
configuration-driven, so repository code can later be run against PostgreSQL
without provider or UI changes.

## Domain and persistence

Milestone 2 introduces provider-neutral contracts in `app/models`, SQLModel
tables and repositories in `app/database`, and application services in
`app/services`. Jobs use a stable source ID first, a canonical URL second, and
a deterministic title/company/location/date fingerprint last. The database
enforces the same identity constraints, preserving idempotency across restarts.

Schema changes use Alembic migrations; the application never calls
`create_all()` at runtime. See [the data model](DATA_MODEL.md) and
[migration guide](MIGRATIONS.md) for operational detail.

## Provider execution

Milestone 3 adds a `BaseProvider` plugin contract. Providers receive only a
saved search's neutral criteria and provider configuration, then yield
`JobCandidate` values. They do not import database, web, scheduler, or export
code. Built-in provider modules are discovered automatically; external
packages can register a provider class under the `job_hunter.providers` entry
point group.

`ManualSearchService` creates durable provider-run records before handing only
their IDs to `BoundedProviderExecutor`. The executor owns a fixed thread pool
and finite semaphore-backed queue, creates a database session within each
worker, upserts candidates through `JobService`, and persists an isolated safe
outcome. This lets API requests return immediately and keeps a failed provider
from affecting other runs.

## Search workspace

Milestone 4 keeps browser rendering in `app/routers` and application behaviour
in `JobWorkspaceService` and `DashboardService`. `SqliteJobWorkspaceRepository`
uses an outer join to the small optional workflow table, so filters, sorting,
pagination, and workflow state require no per-row follow-up queries. The
dashboard read model fetches fixed-size latest-job and recent-search lists.

HTML routes return complete usable pages. Their `/results`, `/summary`, and
`/workflow-panel` counterparts return focused HTMX fragments. Browser forms
remain functional without HTMX through ordinary `303` redirects; HTMX state
changes issue a lightweight trigger that refreshes only dependent sections.

## Exports

Milestone 5 keeps `ExportService` independent of FastAPI and concrete formats.
Its engine-scoped export repository opens a fresh session inside each iterator,
so CSV and JSON streams stay valid after the originating request session ends.
It reads at most 100 records into memory per database batch. XLSX and SQLite
backup adapters use temporary files because their container formats cannot be
sent before finalisation; XLSX is configured for constant-memory writing and
both files are removed when their response stream ends.
