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

## Milestone 1 layout

```text
app/
├── api/          JSON API adapters
├── core/         settings, logging, middleware, errors
├── database/     engine and future repositories
├── exporters/    future export adapters
├── models/       future provider-neutral models
├── providers/    future provider plugins
├── routers/      HTML and HTMX adapters
├── scheduler/    future APScheduler integration
├── services/     future application workflows
├── static/       small CSS, JavaScript, and icon assets
├── templates/    Jinja2 templates
└── main.py       application factory
```

## Resource constraints

The application runs in one Uvicorn process and starts without opening a
database connection. Playwright, JobSpy, spreadsheet support, and scheduling
are optional dependency groups until their milestones. This keeps the base
image and idle process small while preserving a clear path to those features.

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
