"""End-to-end tests for durable recurring saved-search schedules."""

from __future__ import annotations

from time import sleep

from fastapi.testclient import TestClient


def _create_search(client: TestClient) -> str:
    """Create a small saved search and return its durable identifier."""

    response = client.post("/api/v1/searches", json={"name": "Scheduled Python", "criteria": {}})
    assert response.status_code == 201
    return response.json()["id"]


def test_schedule_crud_and_run_history(api_client: TestClient) -> None:
    """Schedules validate their search, persist, update, and expose empty history."""

    search_id = _create_search(api_client)
    response = api_client.post(
        "/api/v1/schedules",
        json={
            "name": "Daily roles",
            "search_id": search_id,
            "trigger_type": "daily",
            "daily_time": "08:30:00",
            "incremental": True,
            "retry_limit": 2,
        },
    )
    assert response.status_code == 201
    schedule = response.json()
    assert schedule["trigger_type"] == "daily"
    assert schedule["last_dispatched_at"] is None

    update = api_client.patch(
        f"/api/v1/schedules/{schedule['id']}", json={"enabled": False, "retry_limit": 0}
    )
    assert update.status_code == 200
    assert update.json()["enabled"] is False

    history = api_client.get(f"/api/v1/schedules/{schedule['id']}/runs")
    assert history.status_code == 200
    assert history.json()["items"] == []

    assert api_client.delete(f"/api/v1/schedules/{schedule['id']}").status_code == 204


def test_schedule_rejects_invalid_trigger_shape(api_client: TestClient) -> None:
    """A daily trigger cannot also carry cron data and cron needs five fields."""

    search_id = _create_search(api_client)
    response = api_client.post(
        "/api/v1/schedules",
        json={
            "name": "Invalid",
            "search_id": search_id,
            "trigger_type": "daily",
            "daily_time": "08:30:00",
            "cron_expression": "0 8 * * *",
        },
    )
    assert response.status_code == 422

    response = api_client.post(
        "/api/v1/schedules",
        json={
            "name": "Invalid cron",
            "search_id": search_id,
            "trigger_type": "cron",
            "cron_expression": "0 8 * *",
        },
    )
    assert response.status_code == 422


def test_schedule_manual_run_persists_dispatch_history(provider_api_client: TestClient) -> None:
    """An immediate schedule run queues providers and writes bounded durable history."""

    provider = provider_api_client.post(
        "/api/v1/providers",
        json={"code": "fixture", "display_name": "Fixture", "enabled": True, "configuration": {}},
    )
    assert provider.status_code == 201
    search_id = _create_search(provider_api_client)
    schedule = provider_api_client.post(
        "/api/v1/schedules",
        json={
            "name": "Manual schedule",
            "search_id": search_id,
            "trigger_type": "cron",
            "cron_expression": "0 8 * * *",
        },
    ).json()

    response = provider_api_client.post(f"/api/v1/schedules/{schedule['id']}/run")
    assert response.status_code == 202

    for _ in range(20):
        history = provider_api_client.get(f"/api/v1/schedules/{schedule['id']}/runs").json()
        if history["items"] and history["items"][0]["provider_run_count"] == 1:
            break
        sleep(0.02)
    assert history["items"][0]["status"] == "queued"
    assert history["items"][0]["manual"] is True
    assert history["items"][0]["provider_run_count"] == 1
