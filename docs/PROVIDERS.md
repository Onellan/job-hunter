# Provider guide

Providers are plugins that turn portal-specific results into the standard
`JobCandidate` contract. A provider never accesses the database, an HTTP route,
the scheduler, or templates. Job-Hunter persists and deduplicates candidates
outside the provider boundary.

## Enable JobSpy

JobSpy is optional so an idle base installation does not import scraping
libraries. Install its focused extra on every process that executes JobSpy:

```powershell
python -m pip install -e ".[jobspy]"
```

Register the provider through the API:

```json
{
  "code": "jobspy",
  "display_name": "JobSpy",
  "enabled": true,
  "configuration": {
    "sites": ["indeed"],
    "country_indeed": "South Africa",
    "results_wanted": 25
  }
}
```

`sites` must be a non-empty list of strings. `results_wanted` is optional and
must be between 1 and 100; it defaults to 25. `location` is an optional provider
fallback when a saved search has no location. `country_indeed` is passed only
when set. Provider configuration must not contain credentials or session
cookies; secret support belongs to the future secure configuration milestone.

Create a saved search with `criteria.provider_codes: ["jobspy"]`, then call:

```text
POST /api/v1/searches/{search_id}/run
```

The `202 Accepted` response contains durable run IDs. Poll
`GET /api/v1/provider-runs/{run_id}` until the status is `succeeded`, `failed`,
or `cancelled`. Missing JobSpy dependencies, invalid provider configuration,
network errors, and malformed provider results are recorded as safe error
categories on the individual run. No provider payloads are logged.

## Enable Pnet

Pnet is a direct Playwright adapter. It uses one short-lived headless Chromium
browser per bounded provider run and parses each loaded result page locally with
BeautifulSoup/lxml. Install the focused extra and its browser binary:

```powershell
python -m pip install -e ".[pnet]"
python -m playwright install chromium
```

Register it with a conservative configuration:

```json
{
  "code": "pnet",
  "display_name": "Pnet",
  "enabled": true,
  "configuration": {
    "max_pages": 2,
    "timeout_ms": 30000,
    "rate_limit_delay_ms": 1000,
    "retry_attempts": 1
  }
}
```

Pnet requires keywords or a Boolean query. It uses Pnet's public HTTPS site
only, fetches at most 10 pages, pauses between pages, and retries only timeout,
rate-limit, and transient browser/source failures (at most two retries). Keep
the default `max_pages: 2` and single provider worker on a 1 GB Raspberry Pi.
The adapter stores no cookies, credentials, profiles, or raw portal HTML.

Portal markup can change. `listing_selector` is an advanced optional setting
for a reviewed Pnet markup change; it is limited in length and should retain a
card-level CSS selector. Parser tests use local recorded fixtures rather than
live portal access.

## Execution limits

Manual runs enter the finite local executor configured by
`provider_execution`. With the defaults, one run scrapes at a time and four
more can wait. If it is full, Job-Hunter records the new run as failed with
`execution_capacity_exhausted`. It does not block an API request or create an
unbounded memory queue.

Use one active worker on a 1 GB Raspberry Pi. Increase to two only after
measuring the enabled provider's CPU and memory use. The executor is local to
one process; it is intentionally not a distributed job queue. Scheduled
retries and incremental searching are introduced in the scheduler milestone.

## Create a built-in provider

Add one module under `app/providers/` with a concrete `BaseProvider` subclass:

```python
from collections.abc import Iterable, Mapping

from pydantic import JsonValue

from app.models.job import JobCandidate
from app.models.search import SearchCriteria
from app.providers.base import BaseProvider


class ExampleProvider(BaseProvider):
    """Return normalised jobs from Example."""

    code = "example"
    display_name = "Example"

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> Iterable[JobCandidate]:
        yield JobCandidate(source=self.code, title="Example role")
```

Discovery imports modules in `app.providers` and registers concrete subclasses
by `code`; no router, service, database, or registry edit is required. Codes
must be unique. Validate configuration early and raise a classified exception
from `app.providers.errors` for expected dependency, configuration, execution,
or parsing failures. Yield valid partial results when possible, and never pass
untrusted portal payloads into log messages.

Tests must use deterministic fixtures or injected transport/scraper functions.
They must not call live job portals.

## Distribute an external plugin

An external Python package can expose a provider class with this packaging
entry point:

```toml
[project.entry-points."job_hunter.providers"]
example = "example_job_hunter.provider:ExampleProvider"
```

The class follows the same `BaseProvider` contract. Install the package in the
application environment, restart Job-Hunter, register its `code` through the
provider API, and enable it. Duplicate or invalid plugin codes fail discovery
at startup rather than routing work to an ambiguous implementation.
