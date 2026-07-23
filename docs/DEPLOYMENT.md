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

Install the normal package with all discovered built-in provider and export
dependencies:

```powershell
python -m pip install .
python -m alembic upgrade head
job-hunter
```

Docker includes Pnet's Chromium browser. On bare metal, the startup diagnostic
inspects only a locally provisioned browser executable. It does not launch a
browser, download software, or contact a provider; a missing browser logs a
safe Pnet-unavailable diagnostic and does not stop the service.

Pnet is intentionally limited to one provider run by the existing
`provider_execution` default. Its Chromium process is short-lived and closes
at the end of each run; do not add application workers on a 1 GB device.

The supplied Docker image installs the same Python dependencies plus Chromium
and its Linux libraries at build time while it is still root. Its portable
Playwright install selects the build platform's supported `linux/amd64` or
`linux/arm64` browser package, then the container drops to the unprivileged
application user. Container startup performs no provider installation or
browser download.

CSV, JSON, SQLite backup, and Excel exports are all available in the normal
runtime installation.

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
