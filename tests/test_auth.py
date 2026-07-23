"""Tests for local bootstrap, password verification, and opaque session cookies."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.database.engine import create_database_engine
from app.main import create_app


def test_local_bootstrap_and_login_issue_safe_cookies(api_client: TestClient) -> None:
    """The first local account is one-time and successful login never returns a password."""
    credentials = {"username": "owner", "password": "correct-horse-battery"}
    created = api_client.post("/api/v1/auth/bootstrap", json=credentials)
    duplicate = api_client.post("/api/v1/auth/bootstrap", json=credentials)
    rejected = api_client.post(
        "/api/v1/auth/login", json={**credentials, "password": "wrong-password-123"}
    )
    logged_in = api_client.post("/api/v1/auth/login", json=credentials)
    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert rejected.status_code == 401
    assert logged_in.status_code == 200
    assert "job_hunter_session" in logged_in.headers["set-cookie"]
    assert "HttpOnly" in logged_in.headers["set-cookie"]


def test_enabled_auth_requires_session_csrf_and_rate_limits(settings) -> None:  # type: ignore[no-untyped-def]
    """Enabled local auth protects browser writes and caps repeated bad credentials."""

    settings.authentication.enabled = True
    settings.authentication.login_max_attempts = 2
    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        credentials = {"username": "owner", "password": "correct-horse-battery"}
        assert client.post("/api/v1/auth/bootstrap", json=credentials).status_code == 201
        assert client.get("/api/v1/jobs").status_code == 401
        assert client.post("/api/v1/auth/login", json=credentials).status_code == 200
        assert client.post("/jobs/actions", data={"action": "bookmark"}).status_code == 403
        assert (
            client.post(
                "/api/v1/auth/login", json={**credentials, "password": "invalid-pass-123"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login", json={**credentials, "password": "invalid-pass-123"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login", json={**credentials, "password": "invalid-pass-123"}
            ).status_code
            == 429
        )
