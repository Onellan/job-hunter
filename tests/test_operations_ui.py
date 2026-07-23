"""Browser regressions for bounded operations history."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_operations_page_has_empty_and_failed_provider_history(api_client: TestClient) -> None:
    """Operations exposes empty history and safe failed provider-run details."""

    empty = api_client.get("/runs")
    provider = api_client.post(
        "/api/v1/providers", json={"code": "operations", "display_name": "Operations"}
    ).json()
    run = api_client.post("/api/v1/provider-runs", json={"provider_id": provider["id"]}).json()
    api_client.patch(
        f"/api/v1/provider-runs/{run['id']}",
        json={
            "status": "failed",
            "error_category": "provider_timeout",
            "error_summary": "Timed out",
        },
    )
    failed = api_client.get("/runs?status=failed")

    assert empty.status_code == 200
    assert "No provider runs match" in empty.text
    assert failed.status_code == 200
    assert "Timed out" in failed.text
    assert f'href="/provider-runs/{run["id"]}"' in failed.text


def test_operations_page_paginates_and_filters_by_provider(api_client: TestClient) -> None:
    """Provider-run history uses bounded pages and retains provider filtering."""

    provider = api_client.post(
        "/api/v1/providers", json={"code": "paging", "display_name": "Paging"}
    ).json()
    for _ in range(26):
        assert (
            api_client.post(
                "/api/v1/provider-runs", json={"provider_id": provider["id"]}
            ).status_code
            == 201
        )

    first = api_client.get(f"/runs?provider_id={provider['id']}")
    second = api_client.get(f"/runs?provider_id={provider['id']}&offset=25")

    assert "Operations pages" in first.text
    assert first.text.count("/provider-runs/") == 25
    assert second.text.count("/provider-runs/") == 1
