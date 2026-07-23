"""Browser regressions for saved-search schedules."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_browser_schedule_lifecycle_and_validation(api_client: TestClient) -> None:
    """A saved-search page creates, edits, and removes a daily schedule locally."""

    search = api_client.post("/api/v1/searches", json={"name": "Scheduled roles"}).json()
    created = api_client.post(
        f"/searches/{search['id']}/schedules",
        data={
            "name": "Morning roles",
            "trigger_type": "daily",
            "daily_time": "08:30",
            "enabled": "true",
            "incremental": "true",
            "retry_limit": "1",
        },
        follow_redirects=False,
    )
    page = api_client.get(f"/searches/{search['id']}")
    schedule = api_client.get("/api/v1/schedules").json()["items"][0]
    updated = api_client.post(
        f"/searches/{search['id']}/schedules/{schedule['id']}",
        data={
            "name": "Paused roles",
            "trigger_type": "daily",
            "daily_time": "09:00",
            "retry_limit": "0",
        },
        follow_redirects=False,
    )
    invalid = api_client.post(
        f"/searches/{search['id']}/schedules",
        data={"name": "Bad cron", "trigger_type": "cron", "cron_expression": "0 8 * *"},
    )
    deleted = api_client.post(
        f"/searches/{search['id']}/schedules/{schedule['id']}/delete", follow_redirects=False
    )

    assert created.status_code == 303
    assert "Morning roles" in page.text
    assert "No dispatches yet" in page.text
    assert updated.status_code == 303
    assert invalid.status_code == 422
    assert "Check cron_expression" in invalid.text
    assert deleted.status_code == 303
