# Job-Hunter Roadmap

## Completed milestones

- [x] Milestone 1 — Foundation
- [x] Milestone 2 — Domain and persistence
- [x] Milestone 3 — Provider platform
- [x] Milestone 4 — Search workspace
- [x] Milestone 5 — Export
- [x] Milestone 6 — Scheduler
- [x] Milestone 7 — Direct Pnet provider
- [x] Milestone 8 — Explainable scoring
- [x] Milestone 9 — Authentication and notifications
- [x] Milestone 10 — Advanced matching

The completed implementation detail for these milestones is retained in the
architecture and feature documentation under `docs/`, the changelog, and the
Git history. The completed UI-review tasks UI-001 through UI-012 are summarised
in `.ai/UI_REVIEW.md`; they are intentionally removed from this active backlog.

## Milestone 11 — Release Quality

- [ ] Run `python scripts/benchmark.py --database data/benchmark.db` on the
      intended Raspberry Pi 4 Model B with 1 GB RAM, using the production-like
      optional features. Record OS image, Python version, enabled extras, idle
      operating-system RSS, startup latency, and dashboard latency in
      `docs/RELEASE.md`.
  - **Acceptance:** idle RSS is below 100 MB, startup is below 3 seconds, and
    dashboard latency is below 1 second on that target device.
- [x] Accessibility, security, backup/restore, Docker, documentation, and
      manual browser release checks. See `docs/RELEASE.md` for the dated local
      baseline and the remaining target-device gate.
- [x] Release notes and reproducible release checklist.

## Built-in provider availability

**Recommended execution order:** PROV-001, then PROV-002. These tasks cover
only the two discovered built-in providers: JobSpy and Pnet.

### PROV-001 — Install the built-in provider runtime in normal deployments

- **Status:** Complete
- **Priority:** Critical
- **Depends on:** None
- **Evidence:** Normal installations now include the discovered provider and
  export dependencies. JobSpy is pinned to the immutable
  `Onellan/JobSpy@7160d0faeda408d246e6948f2cc28ec253883375` metadata-only
  compatibility source (tagged `job-hunter-python-jobspy-1.1.82-numpy-compat.1`),
  which relaxes its upstream exact `NUMPY==1.26.3` metadata requirement without
  changing its public API. Docker is configured to install Chromium before
  dropping privileges; Pnet availability remains a local-only startup
  diagnostic. The startup diagnostic executes its synchronous local Playwright
  path check off FastAPI's event loop, preventing a false Pnet-unavailable
  result in the container. A fresh isolated Python 3.14 editable install,
  Docker Compose config/build/up, local health request, dependency checks, and
  the full quality gate all passed; the Raspberry Pi 1 GB measurement remains
  the separate Milestone 11 hardware acceptance gate.
- **Files:** `pyproject.toml`, `docker/Dockerfile`, `docker/entrypoint.sh`,
  `tests/test_release.py`, `docs/PROVIDERS.md`, `docs/DEPLOYMENT.md`.

#### Scope

Move only the dependencies required by the discovered built-in providers into
the normal runtime installation: JobSpy, Playwright, BeautifulSoup, lxml, and
the existing Excel-export dependency. Pin or otherwise select one compatible
`python-jobspy` release within the current supported range, then derive and
validate the JobSpy `sites` allow-list from that installed release. The default
must use only verified names and be `indeed`, `linkedin`, and `glassdoor` with
`country_indeed: South Africa` and `results_wanted: 25`.

Build Chromium and its Linux dependencies into the Docker image before dropping
privileges, with an architecture-neutral Playwright install that supports
`linux/amd64` and `linux/arm64`. Keep the existing one-worker execution limit.
For bare-metal startup, add only a local dependency/browser diagnostic: do not
contact portals or download browsers at runtime. If an operating-system browser
is absent, Pnet must be reported as unavailable without blocking application
startup; document the platform prerequisite rather than adding a separate
provider-install command.

#### Acceptance criteria

- [x] `docker compose up --build` installs JobSpy, Playwright, Chromium, HTML
      parsing, and existing XLSX export support without a follow-up install.
- [x] `python -m pip install -e ".[dev]"` installs every built-in Python
      dependency; startup safely reports a locally missing Pnet browser rather
      than failing the application.
- [x] The chosen JobSpy release accepts the three default portal names and
      rejects unsupported names before a provider run is queued.
- [x] No live portal request, credential, cookie, CAPTCHA bypass, or browser
      download occurs during installation or startup.

#### Tests

- [x] Extend release/package tests to assert the normal runtime and Docker
      contain the discovered providers' required dependencies and a Chromium
      install step without architecture-specific images.
- [x] Add deterministic JobSpy portal-default and unsupported-site validation
      tests, plus local Pnet dependency/browser diagnostics with imports and
      browser launch mocked as needed.

#### Validation

```bash
pytest tests/test_providers.py tests/test_release.py
ruff check pyproject.toml app/providers docker
mypy app
docker compose build
```

### PROV-002 — Bootstrap discovered provider defaults and expose availability

- **Status:** Complete
- **Priority:** Critical
- **Depends on:** PROV-001
- **Evidence:** The existing `ProviderRegistry` now returns provider-owned
  validated default definitions and local safe availability categories. Startup
  bootstraps only missing rows after migrations and before executor/scheduler
  work; a conflict-safe SQLite insert preserves existing configuration, display
  name, enablement, searches, and schedules. Availability is held only in
  application state and added to the existing provider API/UI response. Fixture
  tests use no portal traffic and cover migrated startup, repeat bootstrap,
  preserved state, and unavailable rendering.
- **Files:** `app/providers/base.py`, `app/providers/jobspy.py`,
  `app/providers/pnet.py`, `app/providers/registry.py`, `app/services/providers.py`,
  `app/database/repositories/providers.py`, `app/services/ports.py`,
  `app/main.py`, `app/api/providers.py`, `app/routers/web.py`,
  `app/templates/providers.html`, `app/templates/provider_detail.html`,
  `tests/test_providers.py`, `tests/test_api_resources.py`,
  `tests/test_provider_ui.py`, `docs/PROVIDERS.md`, `docs/PROVIDER_MANAGEMENT.md`.

#### Scope

Add the smallest provider-owned metadata/default contract to the existing
`BaseProvider` discovery path: stable code, display name, default enabled
state, validated non-secret configuration, and local dependency/browser check.
Use it to bootstrap only missing built-in rows after migrations and before the
scheduler/application begins accepting work. Bootstrap must be SQLite-safe and
idempotent, preserve an existing record's display name, configuration, and
enabled state, and log only code plus a safe availability category.

Use the existing API and provider pages to show bootstrapped rows and an
additive safe availability reason (for example missing Python package or
Chromium executable). Do not persist a transient diagnostic, add a second
registry, seed routes/templates/migrations, or change existing provider APIs
in a breaking way. Pnet remains public, unauthenticated, and conservatively
configured with `max_pages: 2`, `timeout_ms: 30000`,
`rate_limit_delay_ms: 1500`, and `retry_attempts: 1`.

#### Acceptance criteria

- [x] A fresh migrated SQLite database receives exactly one default JobSpy row
      and one default Pnet row discovered from the provider registry.
- [x] Repeated bootstrap creates no duplicates and does not change existing
      configuration, display name, enabled/disabled state, saved searches, or
      schedules.
- [x] Migrations complete before bootstrap; dependency/browser checks are
      local, bounded, and never prevent application startup for one unavailable
      provider.
- [x] `GET /api/v1/providers` and the existing Providers UI show both default
      rows and any safe unavailable reason without exposing secrets.

#### Tests

- [x] Add deterministic fresh-database, repeated-bootstrap, preserved-config,
      preserved-enabled-state, registry/row-alignment, and migration-order
      coverage using temporary SQLite databases.
- [x] Extend API/UI tests for bootstrapped rows and safe unavailable diagnostics;
      retain fixture-only provider tests and prohibit live portal access.
- [x] Add a startup smoke test covering migrations, bootstrap, and an optional
      unavailable provider without provider network traffic.

#### Validation

```bash
pytest tests/test_providers.py tests/test_api_resources.py tests/test_provider_ui.py tests/test_release.py
ruff check app tests
mypy app
python -m alembic upgrade head
docker compose up --build
```
