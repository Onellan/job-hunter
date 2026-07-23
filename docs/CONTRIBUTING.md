# Contributing

## Setup

```powershell
python -m pip install -e ".[dev]"
pre-commit install
```

Run the full local quality gate before opening a pull request:

```powershell
pytest
ruff check .
black --check .
isort --check-only .
mypy app
```

## Test compatibility policy

The development dependency set intentionally uses `httpx2` for FastAPI's
Starlette-based `TestClient`; `httpx` is deprecated by the installed Starlette
test client. It also requires pytest-asyncio 1.x, which is compatible with
Python 3.14's event-loop changes.

Pytest treats `DeprecationWarning` as an error. Do not silence or filter a new
warning in a test. Update the incompatible dependency or test adapter, document
the compatibility decision, and keep the full suite warning-free.

## Project rules

- Keep routes thin and put business decisions in `app/services`.
- Providers must return only the standard domain model and must never import
  database, exporter, scheduler, or template code.
- Repository implementations own persistence; do not put SQL in routes or
  templates.
- Add type hints, docstrings for public APIs, focused tests, documentation, and
  a changelog entry with every milestone change.
- Prefer the smallest dependency and simplest design that meets the requirement.

Read the [provider guide](PROVIDERS.md), [workspace guide](WORKSPACE.md), and
[database migration guide](MIGRATIONS.md) before changing those boundaries.
