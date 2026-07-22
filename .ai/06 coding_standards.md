# Job-Hunter Coding Standards

## Scope

These standards make the codebase predictable and inexpensive to run. Apply
them pragmatically: a small, clear implementation is better than ceremony that
does not improve correctness, security, or maintainability.

## Python and module design

- Target Python 3.12+ and use built-in generic types such as `list[str]`.
- Add `from __future__ import annotations` where it improves forward references
  or import isolation.
- Every public class, function, and method has complete type hints and a
  concise Google-style docstring. Document parameters, return values, raised
  errors, and side effects when they are not obvious.
- Keep a file near 300 lines and a function near 25 lines. At roughly 500 and
  50 lines respectively, split only when doing so makes ownership clearer.
- Use descriptive names. Abbreviate only established terms such as API, URL,
  HTML, ID, and SQL. Name units in variables and constants (`timeout_seconds`,
  `duration_ms`).
- Put meaningful constants near their single use; create a shared constant only
  when it is genuinely shared. Do not hide a clear value behind a pointless
  constant.
- Imports are standard library, third party, then `app` imports. No wildcard
  imports and no imports that create layer violations.

## Architecture and data access

- Pydantic models in `app/models` express provider-neutral contracts. SQLModel
  table mappings and repository implementations stay in `app/database`.
- A route accepts/returns HTTP data and delegates. A service owns the use case.
  A repository owns persistence. A provider owns acquisition/parsing.
- Services receive interfaces/protocols where this isolates an external
  dependency. Do not introduce a dependency-injection framework for simple
  composition in `app/main.py`.
- Use Pydantic validation at external boundaries and parameterised SQLAlchemy
  queries in repositories. Templates receive presentation-ready values only.
- Preserve optional source data as optional. Do not use empty strings, zero
  salaries, or invented dates as stand-ins for missing data.

## Errors and logging

- Catch the narrowest expected exception at the boundary that can recover from
  it. Never use a bare `except` or silently discard an error.
- A broad catch is acceptable only at a resilience boundary (for example a
  health check or provider-run guard), with an explanatory comment and safe
  structured logging.
- Use `logging`, never `print`. Event messages are stable snake_case names
  (`provider_run_failed`, `export_completed`). Attach safe structured context:
  IDs, source, count, duration, outcome, and error category.
- Do not log credentials, cookies, session values, raw resumes, raw provider
  payloads, or full job descriptions. Prefer identifiers and counts.
- Raise domain-specific errors for expected application failures; routes map
  them to safe API or HTML responses in one consistent place.

## Concurrency and resource use

- Use `async` for I/O that is truly asynchronous. Keep CPU work synchronous;
  move blocking provider libraries to a bounded worker thread when needed.
- Every external operation has a timeout, cancellation/cleanup path, and a
  bounded retry policy. Never use unbounded `gather`, queues, result lists, or
  recursive retries.
- Close database sessions, files, HTTP clients, Playwright browsers, and
  temporary resources with context managers or `finally` blocks.
- Fetch only required columns, paginate collections, and stream exports. Do
  not cache a query result merely to avoid writing an index.
- Write to SQLite in short transactions. Never hold a transaction open during
  network I/O, browser automation, rendering, or export generation.

## HTTP, UI, and security

- REST resources use explicit Pydantic request/response models and meaningful
  status codes. Keep `/api/v1` backward-compatible within a released version.
- Prefer server-rendered, semantic HTML. HTMX responses are focused fragments;
  each important interaction also has a usable non-HTMX page/form route.
- Use PicoCSS before custom CSS. Avoid inline scripts/styles; keep any vanilla
  JavaScript small, modular, and free of framework state.
- Validate all request and provider values. Escape output through Jinja2's
  defaults. Never construct SQL or HTML from concatenated user input.
- Add CSRF protection before the first authenticated state-changing browser
  form; configure secure cookies and password hashing with authentication.

## Tests and documentation

- Tests are deterministic, isolated, and fast. Use temporary SQLite databases,
  fixtures, fakes, and recorded HTML; do not call live job portals.
- Treat deprecation warnings as test failures. Fix the incompatible dependency
  or adapter instead of filtering a warning; document any compatibility choice.
- Add unit tests for domain/services, contract tests for adapters, and endpoint
  tests for observable behaviour. A defect fix includes a regression test.
- Update the user-facing documentation, changelog, and roadmap whenever a
  feature, configuration value, or operational behaviour changes.
- Run the project quality gate from `.ai/01 project_rules.md` before handoff.

## Dependency and commit discipline

- Before adding a package, check whether Python or an existing dependency
  solves the problem. Record why a new dependency is needed and keep optional
  heavy features in extras.
- Keep commits focused and use Conventional Commits, for example
  `feat: add provider run repository` or `fix: close browser after timeout`.
- Do not commit generated databases, caches, secrets, provider credentials, or
  unrelated formatting changes.
