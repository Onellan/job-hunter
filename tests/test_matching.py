"""Tests for private deterministic resume skill extraction and job comparison."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ai.resume import extract_skills


def test_skill_extraction_handles_boundaries_and_configured_terms() -> None:
    """Extraction is deterministic, punctuation-safe, and avoids substring false positives."""

    skills = extract_skills("Python, C#, and FastAPI; not pythons.", ["C#", "FastAPI"])
    assert skills == ["c#", "fastapi", "python"]


def test_resume_profile_and_job_comparison_discard_source_text(api_client: TestClient) -> None:
    """The API retains derived skills only and calculates a bounded comparison on demand."""

    first = api_client.post(
        "/api/v1/jobs",
        json={
            "source": "fixture",
            "source_job_id": "match-1",
            "title": "Python engineer",
            "description": "Build FastAPI services with SQL.",
        },
    )
    second = api_client.post(
        "/api/v1/jobs",
        json={
            "source": "fixture",
            "source_job_id": "match-2",
            "title": "Data analyst",
            "description": "Use SQL and Tableau.",
        },
    )
    profile = api_client.put(
        "/api/v1/resume-profile",
        json={"consent": True, "content": "Python, FastAPI, SQL and Tableau experience."},
    )
    comparison = api_client.post(
        "/api/v1/jobs/compare",
        json={"job_ids": [first.json()["job"]["id"], second.json()["job"]["id"]]},
    )
    removed = api_client.delete("/api/v1/resume-profile")
    assert profile.status_code == 200
    assert "content" not in profile.json()
    assert profile.json()["skills"] == ["fastapi", "python", "sql", "tableau"]
    assert comparison.status_code == 200
    assert comparison.json()["common_resume_skills"] == ["sql"]
    assert removed.status_code == 204
    assert api_client.get("/api/v1/resume-profile").status_code == 404
