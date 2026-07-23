"""Deterministic contract and bootstrap coverage for the Careers24 adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine
from app.main import create_app
from app.models.search import SearchCriteria
from app.providers.careers24 import Careers24Provider
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderExecutionError,
    ProviderTimeoutError,
)
from app.providers.registry import ProviderRegistry


def test_registry_discovers_careers24_without_composition_root_changes() -> None:
    """The built-in module is discovered automatically through the provider registry."""

    registry = ProviderRegistry.discover()

    assert "careers24" in registry.codes
    assert registry.create("careers24").display_name == "Careers24"


def test_careers24_provider_parses_public_advert_fixture_with_bounded_pagination() -> None:
    """Public result-card fixtures produce bounded candidates without portal traffic."""

    fixture_html = Path("tests/fixtures/careers24_results.html").read_text(encoding="utf-8")
    loaded_urls: list[str] = []

    def load_page(url: str, _: int) -> str:
        loaded_urls.append(url)
        return fixture_html

    candidates = list(
        Careers24Provider(load_page).search(
            SearchCriteria(keywords=["project", "manager"], locations=["Cape Town"]),
            {"max_pages": 2, "results_wanted": 3, "rate_limit_delay_ms": 500},
        )
    )

    assert loaded_urls == [
        "https://www.careers24.com/jobs/lc-cape-town/kw-project-manager/",
        "https://www.careers24.com/jobs/lc-cape-town/kw-project-manager/?page=2",
    ]
    assert len(candidates) == 2
    assert candidates[0].source == "careers24"
    assert candidates[0].source_job_id == "2361385"
    assert str(candidates[0].source_url) == (
        "https://www.careers24.com/jobs/adverts/2361385-"
        "project-manager-professional-registered-with-sacpcmp-south-africa/"
    )
    assert candidates[0].company == "Dynamic Outsourced Solutions"
    assert candidates[0].location == "Randburg"
    assert candidates[0].employment_type == "full_time"
    assert candidates[0].published_at is not None
    assert candidates[1].workplace_type == "remote"
    assert candidates[1].employment_type == "contract"


def test_careers24_rejects_non_public_base_url_and_visible_access_blocks() -> None:
    """The adapter cannot target another host or treat an access block as no results."""

    criteria = SearchCriteria(keywords=["engineer"])
    with pytest.raises(ProviderConfigurationError):
        list(
            Careers24Provider(lambda _url, _timeout: "").search(criteria, {"base_url": "https://x"})
        )
    with pytest.raises(ProviderExecutionError):
        list(
            Careers24Provider(
                lambda _url, _timeout: "<title>Attention Required! | Cloudflare</title>"
            ).search(criteria, {})
        )


def test_careers24_bootstraps_default_provider_row(settings: Settings) -> None:
    """Discovery-owned defaults create an automatic Careers24 API/UI provider row."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    registry = ProviderRegistry([Careers24Provider])

    with TestClient(create_app(settings, registry)) as client:
        response = client.get("/api/v1/providers")
        provider_page = client.get("/providers")

    assert response.status_code == 200
    provider = response.json()["items"][0]
    assert provider["code"] == "careers24"
    assert provider["display_name"] == "Careers24"
    assert provider["enabled"] is True
    assert provider["availability_reason"] is None
    assert provider["configuration"] == {
        "max_pages": 1,
        "rate_limit_delay_ms": 2000,
        "results_wanted": 20,
        "retry_attempts": 0,
        "timeout_seconds": 15,
    }
    assert provider_page.status_code == 200
    assert "Careers24" in provider_page.text


def test_careers24_transient_timeout_retries_once() -> None:
    """A configured retry is bounded and uses the configured polite delay."""

    calls = 0
    delays: list[float] = []

    def load_page(_: str, __: int) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderTimeoutError()
        return "<html></html>"

    provider = Careers24Provider(load_page, sleeper=delays.append)
    candidates = list(
        provider.search(
            SearchCriteria(keywords=["engineer"]),
            {"retry_attempts": 1, "rate_limit_delay_ms": 500},
        )
    )

    assert candidates == []
    assert calls == 2
    assert delays == [0.5]
