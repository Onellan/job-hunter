# Job-Hunter

Job-Hunter is a lightweight, self-hosted job aggregation platform designed to
run comfortably on a Raspberry Pi 4 with 1 GB of RAM. It combines jobs from
multiple portals into one searchable workspace without coupling providers to
the web application or database.

The project is being delivered in working milestones. Milestone 9 adds an
opt-in, single-user local login boundary with secure session controls and safe
notification delivery adapters while retaining the low-memory local execution
model.

## Quick start

Job-Hunter requires Python 3.12 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m alembic upgrade head
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The health endpoint is available at
<http://127.0.0.1:8000/api/v1/health>.

To execute live JobSpy searches, install its optional dependency as well:

```powershell
python -m pip install -e ".[dev,jobspy]"
```

To enable the direct Pnet adapter, install its focused browser and parser
dependencies, then install the supported Playwright Chromium browser:

```powershell
python -m pip install -e ".[pnet]"
python -m playwright install chromium
```

To enable Excel exports in a production installation, add the focused optional
extra:

```powershell
python -m pip install ".[exports]"
```

Scheduling is included in the normal installation. It uses one in-process
dispatcher thread and the existing bounded provider executor; run a single app
process against a SQLite database.

For a configuration-driven server without reload, use `job-hunter`.

## Docker

```powershell
docker compose up --build
```

The SQLite database is persisted in `data/`. See
[the deployment guide](docs/DEPLOYMENT.md) for configuration and production
notes.

## Development

```powershell
pytest
ruff check .
black --check .
isort --check-only .
mypy app
```

Further documentation:

- [Architecture](docs/ARCHITECTURE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Data model](docs/DATA_MODEL.md)
- [Provider guide](docs/PROVIDERS.md)
- [Provider management](docs/PROVIDER_MANAGEMENT.md)
- [Workspace guide](docs/WORKSPACE.md)
- [Saved-search guide](docs/SEARCHES.md)
- [Export guide](docs/EXPORTS.md)
- [Scheduler guide](docs/SCHEDULER.md)
- [Explainable scoring](docs/SCORING.md)
- [Private resume matching](docs/MATCHING.md)
- [Release checklist](docs/RELEASE.md)
- [Release notes](docs/RELEASE_NOTES.md)
- [Authentication and notifications](docs/AUTHENTICATION.md)
- [API reference](docs/API.md)
- [Database migrations](docs/MIGRATIONS.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
