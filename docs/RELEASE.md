# Release checklist

## Target-device performance evidence

Run this on a Raspberry Pi 4 Model B with 1 GB RAM using the intended optional
features and production-like configuration:

```powershell
python scripts/benchmark.py --database data/benchmark.db
```

Record its output, OS image, Python version, enabled extras, and idle RSS from
the operating system. `python_peak_bytes` is an allocation diagnostic, not
RSS. Accept the release only after confirming idle RSS is below 100 MB, startup
is below 3 seconds, and dashboard latency is below 1 second on that device.

## Security and accessibility

- Use production settings with explicit `trusted_hosts`, authentication, secure
  cookies, and HTTPS through a reverse proxy.
- Create the local account before public exposure.
- Verify login throttling, CSRF rejection, logout, CSP, and response headers.
- Check keyboard navigation, focus visibility, labels, contrast, page zoom, and
  no-JavaScript fallbacks for dashboard, workspace, matching, and login.
- Review reverse-proxy TLS, access logs, and database file permissions.

## Backup and restore drill

1. Stop the application or create a SQLite backup download.
2. Store the database securely: it can contain job notes and derived resume
   skills where enabled.
3. Restore into a separate `data/` directory, run `python -m alembic upgrade
   head`, and start one process with that database.
4. Verify health, workspace records, schedules, and a sample export.

## Reproducible release

```powershell
python -m alembic upgrade head
python -m pytest
python -m ruff check .
python -m black --check .
python -m isort --check-only .
python -m mypy app
git diff --check
docker compose build
```

Tag only after all checks and target-device evidence pass.
