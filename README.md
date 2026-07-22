# Job-Hunter

Job-Hunter is a lightweight, self-hosted job aggregation platform designed to
run comfortably on a Raspberry Pi 4 with 1 GB of RAM. It combines jobs from
multiple portals into one searchable workspace without coupling providers to
the web application or database.

The project is being delivered in working milestones. Milestone 1 provides the
production-oriented application foundation; provider integrations and job
search workflows follow in later milestones.

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
- [API reference](docs/API.md)
- [Database migrations](docs/MIGRATIONS.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
