"""Browser route regressions for saved-search management."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine
from app.main import create_app
from app.providers.registry import ProviderRegistry


def test_saved_search_create_and_edit_forms_are_server_rendered(api_client: TestClient) -> None:
    """A browser user can create and update a reusable search without JSON endpoints."""

    page = api_client.get("/searches")
    created = api_client.post(
        "/searches",
        data={
            "name": "Python roles",
            "keywords": "python, fastapi",
            "locations": "Cape Town",
            "remote_preference": "remote",
            "enabled": "true",
        },
        follow_redirects=False,
    )

    assert page.status_code == 200
    assert 'action="/searches"' in page.text
    assert created.status_code == 303
    detail_url = created.headers["location"]
    assert detail_url.startswith("/searches/")

    updated = api_client.post(
        detail_url,
        data={"name": "Updated Python roles", "remote_preference": "any", "enabled": "true"},
        follow_redirects=False,
    )
    detail = api_client.get(detail_url)

    assert updated.status_code == 303
    assert "Updated Python roles" in detail.text
    assert "python, fastapi" not in detail.text


def test_saved_search_validation_and_run_feedback_stay_in_html(settings: Settings) -> None:
    """Invalid forms and missing providers yield accessible local feedback rather than JSON."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings, ProviderRegistry([]))) as client:
        invalid = client.post("/searches", data={"name": "", "remote_preference": "any"})
        created = client.post(
            "/searches",
            data={"name": "No providers", "enabled": "true"},
            follow_redirects=False,
        )
        detail_url = created.headers["location"]
        run = client.post(
            f"{detail_url}/run",
            headers={"HX-Request": "true"},
        )

    assert invalid.status_code == 422
    assert "form-error" in invalid.text
    assert "Check name" in invalid.text
    assert run.status_code == 200
    assert "No enabled provider matches this saved search" in run.text


def test_saved_search_run_status_links_to_a_safe_browser_detail(
    api_client: TestClient,
) -> None:
    """The saved-search run panel exposes each durable provider-run status to browser users."""

    provider = api_client.post(
        "/api/v1/providers",
        json={"code": "link-provider", "display_name": "Link provider"},
    )
    created = api_client.post(
        "/searches",
        data={"name": "Provider status", "provider_codes": "link-provider", "enabled": "true"},
        follow_redirects=False,
    )
    detail_url = created.headers["location"]
    search_id = detail_url.rsplit("/", maxsplit=1)[-1]
    run = api_client.post(
        "/api/v1/provider-runs",
        json={"provider_id": provider.json()["id"], "search_id": search_id},
    )
    detail = api_client.get(detail_url)
    run_detail = api_client.get(f"/provider-runs/{run.json()['id']}")

    assert provider.status_code == 201
    assert run.status_code == 201
    assert f'href="/provider-runs/{run.json()["id"]}"' in detail.text
    assert run_detail.status_code == 200
    assert "Provider run" in run_detail.text
