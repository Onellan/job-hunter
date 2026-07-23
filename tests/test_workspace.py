"""End-to-end tests for the Milestone 4 job workspace API and HTML routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_blank_browser_filters_redirect_or_push_a_clean_workspace_url(
    api_client: TestClient,
) -> None:
    """Empty optional filter controls never expose a raw validation response."""

    blank_values = "text=&source=&workplace_type=&sort=recent&limit=25"
    page = api_client.get(f"/jobs?{blank_values}", follow_redirects=False)
    fragment = api_client.get(f"/jobs/results?{blank_values}", headers={"HX-Request": "true"})

    assert page.status_code == 303
    assert page.headers["location"] == "/jobs?sort=recent&offset=0&limit=25"
    assert fragment.status_code == 200
    assert fragment.headers["hx-push-url"] == "/jobs?sort=recent&offset=0&limit=25"
    assert "No jobs match these filters" in fragment.text


def test_selected_jobs_compare_without_manual_identifier_entry(api_client: TestClient) -> None:
    """The workspace compares two selected jobs and validates selection bounds locally."""

    first_id = _create_job(api_client, "Platform Engineer", "Cape Town")
    second_id = _create_job(api_client, "Data Analyst", "Durban")
    assert (
        api_client.post(
            "/matching/resume",
            data={
                "content": "Python data analysis FastAPI platform engineering skills",
                "consent": "true",
            },
        ).status_code
        == 200
    )
    comparison = api_client.post("/jobs/compare", data={"job_ids": [first_id, second_id]})
    invalid = api_client.post("/jobs/compare", data={"job_ids": [first_id]})

    assert comparison.status_code == 200
    assert "Comparison" in comparison.text
    assert invalid.status_code == 422
    assert "Check job_ids" in invalid.text


def test_workspace_location_employment_and_date_filters_preserve_browser_query(
    api_client: TestClient,
) -> None:
    """Released workspace filters use durable values and survive HTMX pagination links."""

    recent_id = _create_job(
        api_client,
        "Recent analyst",
        "Cape Town",
        employment_type="full_time",
        published_at=datetime.now(UTC),
    )
    _create_job(
        api_client,
        "Older analyst",
        "Cape Town",
        employment_type="contract",
        published_at=datetime.now(UTC) - timedelta(days=31),
    )
    _create_job(api_client, "Different place", "Durban", employment_type="full_time")

    location = api_client.get("/api/v1/jobs/workspace?location=Cape%20Town")
    employment = api_client.get("/api/v1/jobs/workspace?employment_type=full_time")
    recent = api_client.get("/api/v1/jobs/workspace?posted_within_days=7")
    browser = api_client.get(
        "/jobs/results?location=Cape%20Town&employment_type=full_time&posted_within_days=7",
        headers={"HX-Request": "true"},
    )
    reset = api_client.get("/jobs")

    assert location.json()["total"] == 2
    assert employment.json()["total"] == 2
    assert recent.json()["total"] == 1
    assert recent.json()["items"][0]["job"]["id"] == recent_id
    assert browser.status_code == 200
    assert 'name="location" value="Cape Town"' in browser.text
    assert 'name="employment_type" value="full_time"' in browser.text
    assert 'name="posted_within_days" value="7"' in browser.text
    assert "Reset filters" in reset.text


def test_browser_validation_feedback_is_html_and_preserves_matching_target(
    api_client: TestClient,
) -> None:
    """Browser validation errors are announced as HTML rather than raw API JSON."""

    resume_error = api_client.post("/matching/resume", data={"content": "short"})
    compare_error = api_client.post("/matching/compare", data={"job_ids": "not-a-uuid"})

    assert resume_error.status_code == 422
    assert 'role="alert"' in resume_error.text
    assert "Check consent" in resume_error.text
    assert compare_error.status_code == 422
    assert "We could not complete that request" in compare_error.text
    assert "Request issue" in compare_error.text


def _create_job(
    client: TestClient,
    title: str,
    location: str,
    employment_type: str = "full_time",
    published_at: datetime | None = None,
) -> str:
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
            "employment_type": employment_type,
            "published_at": published_at.isoformat() if published_at else None,
            "description": "A deterministic fixture description.",
        },
    )
    assert response.status_code == 201
    return response.json()["job"]["id"]
