"""Tests for application startup and presentation endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
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

    with TestClient(create_app(settings)) as client:
        response = client.get("/", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert "Job-Hunter" in response.text
    assert response.headers["x-request-id"] == "test-request"
    assert response.headers["x-content-type-options"] == "nosniff"
