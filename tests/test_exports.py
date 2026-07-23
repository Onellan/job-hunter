"""End-to-end tests for bounded export downloads and audit events."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


def test_job_export_endpoints_stream_selected_csv_json_and_xlsx(api_client: TestClient) -> None:
    """All job formats retain selected workflow state and protect spreadsheet formulas."""

    selected_id = _create_job(api_client, "=Formula role")
    _create_job(api_client, "Other role")
    api_client.patch(f"/api/v1/jobs/{selected_id}/workflow", json={"is_bookmarked": True})
    parameters = [("format", "csv"), ("job_ids", selected_id)]

    csv_response = api_client.get("/api/v1/exports/jobs", params=parameters)
    json_response = api_client.get(
        "/api/v1/exports/jobs",
        params=[("format", "json"), ("job_ids", selected_id)],
    )
    xlsx_response = api_client.get(
        "/api/v1/exports/jobs",
        params=[("format", "xlsx"), ("job_ids", selected_id)],
    )
    events = api_client.get("/api/v1/exports/events")
    json_payload = json.loads(json_response.content)

    assert csv_response.status_code == 200
    assert csv_response.headers["content-disposition"].endswith('filename="job-hunter-jobs.csv"')
    assert "'=Formula role" in csv_response.text
    assert json_payload[0]["id"] == selected_id
    assert json_payload[0]["title"] == "=Formula role"
    assert json_payload[0]["is_bookmarked"] is True
    assert json_payload[0]["description"] == "Fixture description."
    assert xlsx_response.status_code == 200
    assert xlsx_response.content.startswith(b"PK")
    with ZipFile(BytesIO(xlsx_response.content)) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
        assert "Formula role" in workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert events.json()["total"] == 3
    assert {event["format"] for event in events.json()["items"]} == {"csv", "json", "xlsx"}


def test_sqlite_backup_export_and_workspace_controls_are_available(api_client: TestClient) -> None:
    """SQLite backup is a file download and the workspace exposes selected-export controls."""

    _create_job(api_client, "Backup role")

    backup = api_client.get("/api/v1/exports/sqlite")
    workspace = api_client.get("/jobs")
    events = api_client.get("/api/v1/exports/events")

    assert backup.status_code == 200
    assert backup.content.startswith(b"SQLite format 3\x00")
    assert backup.headers["content-disposition"].endswith('filename="job-hunter-backup.sqlite"')
    assert "Export selected / filtered" in workspace.text
    assert "SQLite backup" in workspace.text
    assert events.json()["items"][0]["resource"] == "database"
    assert events.json()["items"][0]["selected_job_count"] is None


def test_sqlite_backup_restores_a_queryable_workspace(
    api_client: TestClient, tmp_path: Path
) -> None:
    """A downloaded SQLite backup can be restored and retains durable job data."""

    _create_job(api_client, "Restore role")
    backup = api_client.get("/api/v1/exports/sqlite")
    restored_path = tmp_path / "restored.sqlite"
    restored_path.write_bytes(backup.content)
    engine = create_engine(f"sqlite:///{restored_path}")
    try:
        with engine.connect() as connection:
            title = connection.execute(text("SELECT title FROM jobs")).scalar_one()
    finally:
        engine.dispose()
    assert title == "Restore role"


def _create_job(client: TestClient, title: str) -> str:
    """Create one deterministic job and return its durable identifier."""

    response = client.post(
        "/api/v1/jobs",
        json={
            "source": "fixture",
            "source_job_id": title.lower().replace(" ", "-"),
            "source_url": f"https://jobs.example.test/{title.lower().replace(' ', '-')}",
            "title": title,
            "company": "Example Ltd",
            "location": "Cape Town",
            "workplace_type": "remote",
            "description": "Fixture description.",
        },
    )
    assert response.status_code == 201
    job_id = response.json()["job"]["id"]
    return job_id
