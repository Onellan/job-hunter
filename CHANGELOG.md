# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added

- Milestone 1 application foundation with FastAPI, SQLite, YAML settings,
  structured logging, health checks, Docker support, and quality tooling.
- Milestone 2 provider-neutral job, provider, saved-search, and provider-run
  contracts with SQLModel repositories and application services.
- Versioned CRUD API resources, deterministic durable job deduplication, and
  explicit Alembic schema migrations.
- Warning-free test compatibility: `httpx2` for Starlette's test client and
  pytest-asyncio 1.x for Python 3.14 event-loop support.
