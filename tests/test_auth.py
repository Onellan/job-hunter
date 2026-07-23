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


def test_browser_auth_feedback_and_logout(settings) -> None:  # type: ignore[no-untyped-def]
    """Browser login keeps safe feedback local and logout invalidates the session."""

    settings.authentication.enabled = True
    settings.authentication.login_max_attempts = 2
    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        first_page = client.get("/login")
        bootstrap = client.post(
            "/login/bootstrap",
            data={"username": "owner", "password": "correct-horse-battery"},
            follow_redirects=False,
        )
        after_bootstrap = client.get("/login")
        authenticated = client.post(
            "/login",
            data={"username": "owner", "password": "correct-horse-battery"},
            follow_redirects=False,
        )
        dashboard = client.get("/dashboard")
        csrf = client.cookies.get("job_hunter_csrf")
        logged_out = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
        rejected = client.post(
            "/login",
            data={"username": "owner", "password": "wrong-password-123"},
        )
        rejected_again = client.post(
            "/login",
            data={"username": "owner", "password": "wrong-password-123"},
        )
        throttled = client.post(
            "/login",
            data={"username": "owner", "password": "wrong-password-123"},
        )

    assert "First-time setup" in first_page.text
    assert bootstrap.status_code == 303
    assert "First-time setup" not in after_bootstrap.text
    assert rejected.status_code == 401
    assert "Username or password is incorrect" in rejected.text
    assert "wrong-password-123" not in rejected.text
    assert rejected_again.status_code == 401
    assert throttled.status_code == 429
    assert "Too many sign-in attempts" in throttled.text
    assert "retry-after" in throttled.headers
    assert authenticated.status_code == 303
    assert "owner" in dashboard.text
    assert "Sign out" in dashboard.text
    assert logged_out.status_code == 303
    assert logged_out.headers["location"] == "/login"
