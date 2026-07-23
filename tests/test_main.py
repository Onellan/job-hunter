"""Tests for application startup and presentation endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine
from app.main import create_app


def test_health_endpoint_reports_application_readiness(settings: Settings) -> None:
    """The health endpoint identifies the application and database state."""

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
