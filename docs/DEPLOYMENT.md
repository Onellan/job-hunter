# Deployment

## Docker Compose

Docker is the recommended initial deployment method:

```powershell
docker compose up --build -d
docker compose logs -f
```

Compose binds to `127.0.0.1` by default. Keep it local unless a TLS reverse
proxy is configured with the matching production hostname and authentication.
Never publish the development configuration directly to an untrusted network.

The container runs as a non-root user and stores its SQLite database in the
mounted `data/` directory. Configuration is mounted read-only from `config/`.
Its entry point applies the checked-in Alembic migrations before starting the
single application process.

Before exposing the application, edit `config/config.yaml` (or mount a
production-specific replacement) and set `security.trusted_hosts` to the
public hostname. Place it behind a TLS-terminating reverse proxy such as Nginx.
The image health check calls the local health endpoint after migrations finish.

## Bare-metal service

Install the base package when no live provider adapter is enabled:

```powershell
python -m pip install .
python -m alembic upgrade head
job-hunter
```

To enable the JobSpy adapter, install its focused optional extra before the
service starts:

```powershell
python -m pip install ".[jobspy]"
```

To enable the Pnet Playwright adapter, install its focused extra and Chromium
browser in the derived image or host environment:

```powershell
python -m pip install ".[pnet]"
python -m playwright install --with-deps chromium
```

Pnet is intentionally limited to one provider run by the existing
`provider_execution` default. Its Chromium process is short-lived and closes
at the end of each run; do not add application workers on a 1 GB device.

For Docker, build a small derived image that installs the same extra. Do not
install the broad `providers` extra on a 1 GB device unless its additional
Playwright tooling is required by enabled adapters.

CSV, JSON, and SQLite backup exports work with the base package. Excel export
requires the focused optional extra:

```powershell
python -m pip install ".[exports]"
```

XLSX and SQLite backup downloads use temporary files while keeping RAM bounded.
Ensure the process can write to the operating system temporary directory and
has enough free disk for the requested XLSX or database copy.

Use one application worker on a 1 GB Raspberry Pi. Adding workers duplicates
the Python process and its memory use. Keep the database on local persistent
storage and back up `data/job-hunter.db` before upgrades.

Apply each released migration before a bare-metal upgrade starts serving
traffic. See [Database migrations](MIGRATIONS.md) for backup and rollback
guidance.

## Health check

Use `GET /api/v1/health` for uptime and readiness monitoring. It reports the
database connectivity state without exposing database credentials.
