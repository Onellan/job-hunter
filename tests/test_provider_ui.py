"""Browser route regressions for provider management."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from fastapi.testclient import TestClient
from pydantic import JsonValue
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database.engine import create_database_engine
from app.main import create_app
from app.models.job import JobCandidate
from app.models.search import SearchCriteria
from app.providers.base import BaseProvider
from app.providers.registry import ProviderRegistry


class _UnavailableProvider(BaseProvider):
    """Provider fixture that exposes a safe local availability category."""

    code = "unavailable"
    display_name = "Unavailable provider"
    bootstrap_by_default = True

    @classmethod
    def availability_reason(cls) -> str:
        """Return the safe category shown by API and provider pages."""

        return "browser_unavailable"

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> Iterable[JobCandidate]:
        """Return no fixture results because this test exercises only startup metadata."""

        return []


def test_provider_browser_create_edit_enablement_and_delete_confirmation(
    api_client: TestClient,
) -> None:
    """Provider management is available through progressive HTML forms."""

    created = api_client.post(
        "/providers",
        data={
            "code": "fixture-ui",
            "display_name": "Fixture UI",
            "configuration": '{"limit": 10}',
            "enabled": "true",
        },
        follow_redirects=False,
    )
    detail_url = created.headers["location"]
    updated = api_client.post(
        detail_url,
        data={"display_name": "Disabled fixture", "configuration": "{}"},
        follow_redirects=False,
    )
    detail = api_client.get(detail_url)
    unconfirmed = api_client.post(f"{detail_url}/delete", data={})
    deleted = api_client.post(
        f"{detail_url}/delete", data={"confirm_delete": "true"}, follow_redirects=False
    )

    assert created.status_code == 303
    assert updated.status_code == 303
    assert "Disabled fixture" in detail.text
    assert "Disabled provider configuration" in detail.text
    assert unconfirmed.status_code == 422
    assert "Select the confirmation checkbox" in unconfirmed.text
    assert deleted.status_code == 303
    assert deleted.headers["location"] == "/providers"


def test_provider_configuration_rejection_never_echoes_submitted_secret(
    api_client: TestClient,
) -> None:
    """Browser and JSON API paths reject credential-like configuration keys safely."""

    secret_value = "not-for-browser-storage"
    browser = api_client.post(
        "/providers",
        data={
            "code": "unsafe-ui",
            "display_name": "Unsafe UI",
            "configuration": '{"nested": {"apiToken": "not-for-browser-storage"}}',
        },
    )
    api = api_client.post(
        "/api/v1/providers",
        json={
            "code": "unsafe-api",
            "display_name": "Unsafe API",
            "configuration": {"token": secret_value},
        },
    )

    assert browser.status_code == 422
    assert "credentials" in browser.text.lower()
    assert secret_value not in browser.text
    assert api.status_code == 422


def test_provider_api_and_ui_include_safe_transient_availability(settings: Settings) -> None:
    """Runtime availability is shown without being stored in provider configuration."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    registry = ProviderRegistry([_UnavailableProvider])

    with TestClient(create_app(settings, registry)) as client:
        providers = client.get("/api/v1/providers").json()["items"]
        provider = providers[0]
        detail = client.get(f"/providers/{provider['id']}")
        page = client.get("/providers")

    assert provider["availability_reason"] == "browser_unavailable"
    assert "browser unavailable" in page.text
    assert "Local runtime unavailable: browser unavailable." in detail.text
    assert "availability_reason" not in provider["configuration"]
