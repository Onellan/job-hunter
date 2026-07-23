"""Browser route regressions for provider management."""

from __future__ import annotations

from fastapi.testclient import TestClient


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
