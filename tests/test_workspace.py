"""End-to-end tests for the Milestone 4 job workspace API and HTML routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_workspace_api_filters_jobs_and_persists_workflow_state(api_client: TestClient) -> None:
    """Bookmarks, applied state, notes, and bulk actions remain separate from source jobs."""

    first_id = _create_job(api_client, "Python Engineer", "Remote")
    second_id = _create_job(api_client, "Business Analyst", "Johannesburg")

    workspace = api_client.get("/api/v1/jobs/workspace?text=engineer&workplace_type=remote")
    workflow = api_client.patch(
        f"/api/v1/jobs/{first_id}/workflow",
        json={"is_bookmarked": True, "notes": "Ask about the data platform."},
    )
    bookmarked = api_client.get("/api/v1/jobs/workspace?bookmarked=true")
    bulk = api_client.post(
        "/api/v1/jobs/workflow/bulk",
        json={"job_ids": [first_id, second_id], "action": "mark_applied"},
    )
    detail = api_client.get(f"/api/v1/jobs/{first_id}/workspace")
    score = api_client.get(f"/api/v1/jobs/{first_id}/score")

    assert workspace.status_code == 200
    assert workspace.json()["total"] == 1
    assert workflow.status_code == 200
    assert workflow.json()["notes"] == "Ask about the data platform."
    assert bookmarked.json()["items"][0]["job"]["id"] == first_id
    assert bulk.json() == {"updated_count": 2}
    assert detail.json()["workflow"] == {
        "is_bookmarked": True,
        "is_applied": True,
        "notes": "Ask about the data platform.",
    }
    assert score.json()["score"] == {
        "score": 0,
        "confidence": 0,
        "matched_skills": [],
        "missing_skills": [],
        "reasons": ["Configure scoring preferences to calculate a match score."],
    }


def test_workspace_html_routes_render_fragments_and_accept_browser_forms(
    api_client: TestClient,
) -> None:
    """The browser workspace works as full pages and uses focused HTMX responses."""

    job_id = _create_job(api_client, "Data Engineer", "Cape Town")

    dashboard = api_client.get("/dashboard")
    jobs_page = api_client.get("/jobs?text=data")
    results = api_client.get("/jobs/results?text=data", headers={"HX-Request": "true"})
    htmx_update = api_client.post(
        f"/jobs/{job_id}/workflow",
        data={"is_bookmarked": "true", "return_to": "/jobs"},
        headers={"HX-Request": "true"},
    )
    fallback_update = api_client.post(
        f"/jobs/{job_id}/workflow",
        data={"notes": "Follow up next week", "return_to": f"/jobs/{job_id}"},
        follow_redirects=False,
    )
    detail = api_client.get(f"/jobs/{job_id}")

    assert dashboard.status_code == 200
    assert "Jobs found today" in dashboard.text
    assert jobs_page.status_code == 200
    assert "Data Engineer" in jobs_page.text
    assert results.status_code == 200
    assert 'id="job-results"' in results.text
    assert htmx_update.status_code == 204
    assert htmx_update.headers["hx-trigger"] == "jobs-updated"
    assert fallback_update.status_code == 303
    assert fallback_update.headers["location"] == f"/jobs/{job_id}"
    assert "Follow up next week" in detail.text
    assert "Match score" in detail.text


def _create_job(client: TestClient, title: str, location: str) -> str:
    """Create a deterministic remote job and return its durable identifier."""

    response = client.post(
        "/api/v1/jobs",
        json={
            "source": "fixture",
            "source_job_id": title.lower().replace(" ", "-"),
            "source_url": f"https://jobs.example.test/{title.lower().replace(' ', '-')}",
            "title": title,
            "company": "Example Ltd",
            "location": location,
            "workplace_type": "remote",
            "description": "A deterministic fixture description.",
        },
    )
    assert response.status_code == 201
    return response.json()["job"]["id"]
