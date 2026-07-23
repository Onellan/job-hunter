"""Tests for application startup and presentation endpoints."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine
from app.main import create_app
from app.providers.jobspy import JobSpyProvider
from app.providers.pnet import PnetProvider
from app.providers.registry import ProviderRegistry


def test_health_endpoint_reports_application_readiness(settings: Settings) -> None:
    """The health endpoint identifies the application and database state."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "Job-Hunter",
        "version": "test",
        "environment": "testing",
        "database": {"status": "ok"},
    }


def test_provider_discovery_runtime_checks_run_outside_the_lifespan_event_loop(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synchronous local provider checks cannot execute on FastAPI's event loop."""

    ran_on_event_loop: list[bool] = []

    def definitions(_: ProviderRegistry) -> tuple[object, ...]:
        """Record whether discovery-owned local checks execute on an async loop."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            ran_on_event_loop.append(False)
        else:
            ran_on_event_loop.append(True)
        return ()

    monkeypatch.setattr(ProviderRegistry, "definitions", definitions)

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()

    with TestClient(create_app(settings)):
        pass

    assert ran_on_event_loop == [False]


def test_startup_bootstraps_defaults_without_replacing_user_provider_state(
    settings: Settings,
) -> None:
    """Migration-ready startup creates only missing provider rows before scheduler work."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    registry = ProviderRegistry([JobSpyProvider, PnetProvider])

    with TestClient(create_app(settings, registry)) as client:
        providers = client.get("/api/v1/providers").json()["items"]
        providers_by_code = {provider["code"]: provider for provider in providers}
        jobspy = providers_by_code["jobspy"]
        pnet = providers_by_code["pnet"]
        assert set(providers_by_code) == {"jobspy", "pnet"}
        assert jobspy["configuration"] == {
            "sites": ["indeed", "linkedin"],
            "country_indeed": "South Africa",
            "results_wanted": 25,
        }
        assert pnet["configuration"] == {
            "max_pages": 2,
            "timeout_ms": 30000,
            "rate_limit_delay_ms": 1500,
            "retry_attempts": 1,
        }
        updated = client.patch(
            f"/api/v1/providers/{jobspy['id']}",
            json={
                "display_name": "My JobSpy",
                "enabled": False,
                "configuration": {"sites": ["indeed"], "results_wanted": 10},
            },
        )
        search = client.post("/api/v1/searches", json={"name": "Python roles", "criteria": {}})
        schedule = client.post(
            "/api/v1/schedules",
            json={
                "name": "Future daily run",
                "search_id": search.json()["id"],
                "trigger_type": "daily",
                "daily_time": "23:59:00",
            },
        )

    assert updated.status_code == 200
    assert search.status_code == 201
    assert schedule.status_code == 201

    with TestClient(create_app(settings, registry)) as client:
        providers = client.get("/api/v1/providers").json()["items"]
        providers_by_code = {provider["code"]: provider for provider in providers}
        assert len(providers_by_code) == 2
        assert providers_by_code["jobspy"]["display_name"] == "My JobSpy"
        assert providers_by_code["jobspy"]["enabled"] is False
        assert providers_by_code["jobspy"]["configuration"] == {
            "sites": ["indeed"],
            "results_wanted": 10,
        }
        assert client.get("/api/v1/searches").json()["total"] == 1
        assert client.get("/api/v1/schedules").json()["total"] == 1


def test_home_page_has_security_and_request_headers(settings: Settings) -> None:
    """The initial web UI is available with baseline HTTP protections."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        response = client.get("/", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert "Job-Hunter" in response.text
    assert 'href="#main-content"' in response.text
    assert 'id="main-content"' in response.text
    assert '<meta name="htmx-config" content=\'{"includeIndicatorStyles":false}\'>' in response.text
    assert response.text.index('name="htmx-config"') < response.text.index("htmx.org@2.0.4")
    assert response.headers["x-request-id"] == "test-request"
    assert response.headers["x-content-type-options"] == "nosniff"
    content_security_policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in content_security_policy
    assert "'unsafe-inline'" not in content_security_policy
    assert "object-src 'none'" in content_security_policy


def test_mobile_navigation_rules_preserve_wrapping_and_touch_targets() -> None:
    """Narrow layouts keep primary navigation and form controls within the viewport."""

    stylesheet = (Path(__file__).resolve().parents[1] / "app/static/css/app.css").read_text()

    assert "@media (max-width: 900px)" in stylesheet
    assert ".app-header nav { align-items: flex-start; flex-wrap: wrap;" in stylesheet
    assert ".app-header nav ul:last-child { width: 100%; }" in stylesheet
    assert ".app-header nav a { min-height: 2.75rem; }" in stylesheet
