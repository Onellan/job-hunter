"""Tests for provider discovery, JobSpy normalisation, and manual execution."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from threading import Event
from time import sleep
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.config import ProviderExecutionSettings, Settings
from app.database.engine import create_database_engine
from app.models.search import SearchCriteria
from app.providers.errors import ProviderConfigurationError
from app.providers.execution import BoundedProviderExecutor
from app.providers.jobspy import DEFAULT_SITES, JobSpyProvider, _build_jobspy_arguments
from app.providers.pnet import PnetProvider, PnetSettings, check_pnet_runtime
from app.providers.registry import ProviderRegistry


class _FakeDataFrame:
    """Minimal dataframe substitute used to avoid importing pandas in tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        """Store deterministic JobSpy-style rows."""

        self._rows = rows

    def to_dict(self, orient: str) -> list[dict[str, object]]:
        """Return records in the only orientation requested by the adapter."""

        assert orient == "records"
        return self._rows


def test_registry_discovers_the_built_in_jobspy_plugin() -> None:
    """Adding a provider module makes its plugin available without service edits."""

    registry = ProviderRegistry.discover()

    assert "jobspy" in registry.codes
    assert registry.create("jobspy").display_name == "JobSpy"
    assert registry.create("pnet").display_name == "Pnet"


def test_pnet_provider_parses_recorded_pages_with_bounded_pagination() -> None:
    """Pnet HTML fixtures yield valid partial cards without a live browser or portal call."""

    fixture_html = (Path("tests/fixtures/pnet_results.html")).read_text(encoding="utf-8")
    loaded_urls: list[str] = []

    def load_pages(urls: Sequence[str], _: PnetSettings) -> list[str]:
        loaded_urls.extend(urls)
        return [fixture_html for _ in urls]

    candidates = list(
        PnetProvider(load_pages).search(
            SearchCriteria(keywords=["data", "engineer"], locations=["Cape Town"]),
            {"max_pages": 2, "rate_limit_delay_ms": 250},
        )
    )

    assert len(loaded_urls) == 2
    assert loaded_urls[0].startswith("https://www.pnet.co.za/jobs/data-engineer?")
    assert "location=Cape+Town" in loaded_urls[0]
    assert candidates[0].source == "pnet"
    assert candidates[0].source_job_id == "pnet-1001"
    assert str(candidates[0].source_url) == "https://www.pnet.co.za/jobs/data-engineer-1001"
    assert candidates[0].workplace_type == "remote"
    assert candidates[1].employment_type == "contract"


def test_pnet_provider_rejects_unbounded_or_non_pnet_configuration() -> None:
    """Pnet cannot be pointed at arbitrary hosts or given an unsafe page count."""

    provider = PnetProvider(lambda _urls, _settings: [])
    criteria = SearchCriteria(keywords=["python"])

    with pytest.raises(ProviderConfigurationError):
        list(provider.search(criteria, {"base_url": "https://example.test/jobs"}))
    with pytest.raises(ProviderConfigurationError):
        list(provider.search(criteria, {"max_pages": 11}))


def test_pnet_retries_timeout_with_capped_backoff() -> None:
    """A transient timeout retries once and applies the configured polite delay."""

    class FakeTimeout(Exception):
        """Simulate the Playwright timeout type without importing Playwright."""

    class FakePage:
        """Return content after one deterministic timeout."""

        def __init__(self) -> None:
            self.calls = 0

        def goto(self, _: str, wait_until: str) -> object:
            assert wait_until == "domcontentloaded"
            self.calls += 1
            if self.calls == 1:
                raise FakeTimeout()
            return None

        def content(self) -> str:
            return "<html></html>"

    delays: list[float] = []
    provider = PnetProvider(sleeper=delays.append)
    content = provider._load_page_with_retry(
        FakePage(),
        "https://www.pnet.co.za/jobs/python?page=1",
        PnetSettings(retry_attempts=1, rate_limit_delay_ms=250),
        FakeTimeout,
        RuntimeError,
    )

    assert content == "<html></html>"
    assert delays == [0.25]


def test_jobspy_provider_normalises_a_fixture_without_live_network_access() -> None:
    """JobSpy tabular output is converted to the standard job candidate contract."""

    captured_arguments: dict[str, object] = {}

    def scrape_jobs(**arguments: object) -> _FakeDataFrame:
        captured_arguments.update(arguments)
        return _FakeDataFrame(
            [
                {
                    "id": "jobspy-1",
                    "job_url": "https://jobs.example.test/jobspy-1",
                    "title": "Data Engineer",
                    "company": "Example Ltd",
                    "location": "Johannesburg",
                    "is_remote": True,
                    "job_type": "full-time",
                    "min_amount": "100000",
                    "max_amount": "120000",
                    "currency": "ZAR",
                    "interval": "yearly",
                    "date_posted": "2026-07-22T10:00:00Z",
                }
            ]
        )

    candidates = list(
        JobSpyProvider(scrape_jobs).search(
            SearchCriteria(keywords=["data", "engineer"], posted_within_days=7),
            {"sites": ["indeed"], "results_wanted": 10},
        )
    )

    assert captured_arguments["search_term"] == "data engineer"
    assert captured_arguments["hours_old"] == 168
    assert candidates[0].source == "jobspy"
    assert candidates[0].workplace_type == "remote"
    assert candidates[0].employment_type == "full_time"
    assert candidates[0].salary_currency == "ZAR"
    assert candidates[0].salary_period == "year"


def test_jobspy_uses_the_supported_default_sites_and_south_africa_country() -> None:
    """The selected JobSpy release receives only the verified provider defaults."""

    arguments = _build_jobspy_arguments(SearchCriteria(keywords=["engineer"]), {})

    assert arguments["site_name"] == list(DEFAULT_SITES)
    assert arguments["country_indeed"] == "South Africa"
    assert arguments["results_wanted"] == 25


def test_jobspy_rejects_sites_outside_the_supported_allow_list() -> None:
    """An unsupported portal name is rejected before the scraper can make a request."""

    with pytest.raises(ProviderConfigurationError, match="google"):
        _build_jobspy_arguments(SearchCriteria(keywords=["engineer"]), {"sites": ["google"]})


def test_pnet_runtime_check_reports_a_missing_local_browser_without_launching(
    monkeypatch: MonkeyPatch,
) -> None:
    """The startup diagnostic checks only a mocked local executable path."""

    def missing_browser_path() -> str:
        return "C:/missing/playwright/chromium"

    monkeypatch.setattr("app.providers.pnet._chromium_executable_path", missing_browser_path)

    assert check_pnet_runtime() == "browser_unavailable"


def test_pnet_runtime_check_reports_a_missing_python_dependency(
    monkeypatch: MonkeyPatch,
) -> None:
    """The startup diagnostic classifies a missing local Playwright import safely."""

    def missing_playwright() -> str:
        raise ModuleNotFoundError("playwright")

    monkeypatch.setattr("app.providers.pnet._chromium_executable_path", missing_playwright)

    assert check_pnet_runtime() == "dependency_unavailable"


def test_manual_execution_is_non_blocking_and_isolates_provider_failures(
    provider_api_client: TestClient,
) -> None:
    """One provider failure does not prevent a successful fixture provider from storing jobs."""

    provider_ids = _create_fixture_providers(provider_api_client)
    search = provider_api_client.post(
        "/api/v1/searches",
        json={
            "name": "Fixture roles",
            "criteria": {"keywords": ["engineer"], "provider_codes": list(provider_ids)},
        },
    )

    started = provider_api_client.post(f"/api/v1/searches/{search.json()['id']}/run")

    assert started.status_code == 202
    run_ids = [run["id"] for run in started.json()["provider_runs"]]
    completed_runs = list(_wait_for_terminal_runs(provider_api_client, run_ids))
    statuses = {run["status"] for run in completed_runs}

    assert statuses == {"succeeded", "failed"}
    assert provider_api_client.get("/api/v1/jobs").json()["total"] == 1


def test_bounded_executor_rejects_work_when_its_capacity_is_full(
    settings: Settings,
    monkeypatch: MonkeyPatch,
) -> None:
    """The executor must reject excess work rather than build an unbounded queue."""

    engine = create_database_engine(settings.database)
    executor = BoundedProviderExecutor(
        engine,
        ProviderRegistry([]),
        ProviderExecutionSettings(max_concurrent_runs=1, max_queued_runs=0),
    )
    started = Event()
    release = Event()

    def block(_: object) -> None:
        started.set()
        assert release.wait(timeout=1)

    monkeypatch.setattr(executor, "_execute_safely", block)
    try:
        assert executor.submit(uuid4())
        assert started.wait(timeout=1)
        assert not executor.submit(uuid4())
    finally:
        release.set()
        executor.shutdown()
        engine.dispose()


def _create_fixture_providers(client: TestClient) -> set[str]:
    """Register deterministic fixture rows and return their configured codes."""

    registrations = (
        {"code": "fixture", "display_name": "Fixture Provider"},
        {"code": "fixture-failing", "display_name": "Failing Fixture Provider"},
    )
    for registration in registrations:
        assert client.post("/api/v1/providers", json=registration).status_code == 201
    return {registration["code"] for registration in registrations}


def _wait_for_terminal_runs(client: TestClient, run_ids: list[str]) -> Iterator[dict[str, object]]:
    """Poll short-lived fixture runs without making the API handler block on scraping."""

    for _ in range(100):
        runs = [client.get(f"/api/v1/provider-runs/{run_id}").json() for run_id in run_ids]
        if all(run["status"] in {"succeeded", "failed", "cancelled"} for run in runs):
            yield from runs
            return
        sleep(0.01)
    raise AssertionError("Fixture provider runs did not finish within one second")
