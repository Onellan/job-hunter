"""End-to-end tests for the Milestone 2 JSON resource API."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_job_upsert_deduplicates_and_exposes_crud(api_client: TestClient) -> None:
    """Stable source identity makes repeated job ingestion idempotent."""

    candidate = {
        "source": "jobspy",
        "source_job_id": "listing-1",
        "source_url": "https://jobs.example.test/listing-1",
        "title": "Python Engineer",
        "company": "Example Ltd",
        "location": "Cape Town",
        "workplace_type": "remote",
        "salary_min": "100000.00",
        "salary_max": "120000.00",
        "salary_currency": "ZAR",
        "salary_period": "year",
    }
    created = api_client.post("/api/v1/jobs", json=candidate)
    refreshed = api_client.post(
        "/api/v1/jobs",
        json={**candidate, "description": "Updated source description."},
    )

    assert created.status_code == 201
    assert created.json()["created"] is True
    assert refreshed.status_code == 200
    assert refreshed.json()["created"] is False
    assert refreshed.json()["job"]["id"] == created.json()["job"]["id"]

    job_id = created.json()["job"]["id"]
    listed = api_client.get("/api/v1/jobs?source=jobspy")
    updated = api_client.patch(f"/api/v1/jobs/{job_id}", json={"location": "Remote"})
    deleted = api_client.delete(f"/api/v1/jobs/{job_id}")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert updated.status_code == 200
    assert updated.json()["location"] == "Remote"
    assert deleted.status_code == 204
    assert api_client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_job_fallback_fingerprint_deduplicates_cross_provider_results(
    api_client: TestClient,
) -> None:
    """The fallback fingerprint prevents duplicate rows without source IDs or URLs."""

    first = api_client.post(
        "/api/v1/jobs",
        json={
            "source": "portal-a",
            "title": "Business Analyst",
            "company": "Example Ltd",
            "location": "Johannesburg",
            "published_at": "2026-07-20T09:00:00Z",
        },
    )
    second = api_client.post(
        "/api/v1/jobs",
        json={
            "source": "portal-b",
            "title": "Business Analyst",
            "company": "Example Ltd",
            "location": "Johannesburg",
            "published_at": "2026-07-20T15:00:00Z",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["job"]["source"] == "portal-a"


def test_provider_search_and_run_resources_enforce_lifecycle(api_client: TestClient) -> None:
    """Provider runs validate references, record timestamps, and reject bad transitions."""

    provider = api_client.post(
        "/api/v1/providers",
        json={"code": "jobspy", "display_name": "JobSpy", "configuration": {"limit": 25}},
    )
    search = api_client.post(
        "/api/v1/searches",
        json={
            "name": "Python roles",
            "criteria": {"keywords": ["python"], "remote_preference": "remote"},
        },
    )
    provider_id = provider.json()["id"]
    search_id = search.json()["id"]
    created_run = api_client.post(
        "/api/v1/provider-runs",
        json={"provider_id": provider_id, "search_id": search_id},
    )

    assert provider.status_code == 201
    assert search.status_code == 201
    assert created_run.status_code == 201
    run_id = created_run.json()["id"]

    running = api_client.patch(f"/api/v1/provider-runs/{run_id}", json={"status": "running"})
    complete = api_client.patch(
        f"/api/v1/provider-runs/{run_id}",
        json={"status": "succeeded", "result_count": 3},
    )
    invalid_transition = api_client.patch(
        f"/api/v1/provider-runs/{run_id}",
        json={"status": "running"},
    )

    assert running.status_code == 200
    assert running.json()["started_at"] is not None
    assert complete.status_code == 200
    assert complete.json()["finished_at"] is not None
    assert complete.json()["result_count"] == 3
    assert invalid_transition.status_code == 409


def test_provider_and_search_crud_preserve_history_references(api_client: TestClient) -> None:
    """Search deletion nulls historical run references while provider deletion is protected."""

    provider = api_client.post(
        "/api/v1/providers",
        json={"code": "careers", "display_name": "Careers"},
    )
    search = api_client.post("/api/v1/searches", json={"name": "Analyst roles"})
    provider_id = provider.json()["id"]
    search_id = search.json()["id"]
    run = api_client.post(
        "/api/v1/provider-runs",
        json={"provider_id": provider_id, "search_id": search_id},
    )

    assert (
        api_client.patch(
            f"/api/v1/providers/{provider_id}",
            json={"enabled": False},
        ).json()["enabled"]
        is False
    )
    assert (
        api_client.patch(
            f"/api/v1/searches/{search_id}",
            json={"criteria": {"excluded_keywords": ["intern"]}},
        ).status_code
        == 200
    )
    assert api_client.delete(f"/api/v1/searches/{search_id}").status_code == 204
    assert api_client.get(f"/api/v1/provider-runs/{run.json()['id']}").json()["search_id"] is None
    assert api_client.delete(f"/api/v1/providers/{provider_id}").status_code == 409
    assert api_client.delete(f"/api/v1/provider-runs/{run.json()['id']}").status_code == 204
    assert api_client.delete(f"/api/v1/providers/{provider_id}").status_code == 204
