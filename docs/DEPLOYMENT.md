# Deployment

## Docker Compose

Docker is the recommended initial deployment method:

```powershell
docker compose up --build -d
docker compose logs -f
```

The container runs as a non-root user and stores its SQLite database in the
mounted `data/` directory. Configuration is mounted read-only from `config/`.
Its entry point applies the checked-in Alembic migrations before starting the
single application process.

Before exposing the application, edit `config/config.yaml` (or mount a
production-specific replacement) and set `security.trusted_hosts` to the
public hostname. Place it behind a TLS-terminating reverse proxy such as Nginx.

## Bare-metal service

Install only the base package for the foundation:

```powershell
python -m pip install .
python -m alembic upgrade head
job-hunter
```

Use one application worker on a 1 GB Raspberry Pi. Adding workers duplicates
the Python process and its memory use. Keep the database on local persistent
storage and back up `data/job-hunter.db` before upgrades.

Apply each released migration before a bare-metal upgrade starts serving
traffic. See [Database migrations](MIGRATIONS.md) for backup and rollback
guidance.

## Health check

Use `GET /api/v1/health` for uptime and readiness monitoring. It reports the
database connectivity state without exposing database credentials.
