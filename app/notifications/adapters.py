"""Small standard-library adapters for configured notification channels."""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import Request, urlopen

from app.core.config import NotificationSettings
from app.models.notification import NotificationChannel

_REQUEST_TIMEOUT_SECONDS = 10


class NotificationAdapter(Protocol):
    """Deliver a short operational event without exposing the recipient in history."""

    def send(self, event_type: str) -> None:
        """Deliver the event or raise an expected transport/configuration exception."""


class EmailAdapter:
    """Send a test event using a deployment-provided SMTP URL."""

    def __init__(self, url: str) -> None:
        self._url = url

    def send(self, event_type: str) -> None:
        """Send a minimal message through an SMTP URL with explicit query recipients."""

        parsed = urlsplit(self._url)
        recipients = parse_qs(parsed.query).get("to", [])
        sender = parse_qs(parsed.query).get("from", [None])[-1]
        if (
            parsed.scheme not in {"smtp", "smtps"}
            or not parsed.hostname
            or not recipients
            or not sender
        ):
            raise ValueError("email_url must be smtp(s)://user:password@host?from=x&to=y")
        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = "Job-Hunter notification test"
        message.set_content(f"Job-Hunter event: {event_type}")
        connection_type = smtplib.SMTP_SSL if parsed.scheme == "smtps" else smtplib.SMTP
        with connection_type(
            parsed.hostname, parsed.port or (465 if parsed.scheme == "smtps" else 587), timeout=10
        ) as client:
            if parsed.scheme == "smtp":
                client.starttls()
            if parsed.username:
                client.login(unquote(parsed.username), unquote(parsed.password or ""))
            client.send_message(message)


class WebhookAdapter:
    """Send a compact JSON event to an explicitly configured webhook."""

    def __init__(self, url: str, payload: dict[str, str]) -> None:
        self._url = url
        self._payload = payload

    def send(self, event_type: str) -> None:
        """Post channel-compatible minimal payload with a bounded timeout."""

        payload = {**self._payload, "text": f"Job-Hunter: {event_type}"}
        request = Request(
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            if not 200 <= response.status < 300:
                raise OSError(f"Webhook responded with HTTP {response.status}")


def configured_adapter(
    settings: NotificationSettings, channel: NotificationChannel
) -> NotificationAdapter | None:
    """Return an adapter only for a complete opted-in channel configuration."""

    if not settings.enabled:
        return None
    if channel is NotificationChannel.EMAIL and settings.email_url:
        return EmailAdapter(settings.email_url)
    if channel is NotificationChannel.TELEGRAM:
        if settings.telegram_bot_token and settings.telegram_chat_id:
            endpoint = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            return WebhookAdapter(endpoint, {"chat_id": settings.telegram_chat_id})
    urls = {
        NotificationChannel.SLACK: settings.slack_webhook_url,
        NotificationChannel.TEAMS: settings.teams_webhook_url,
    }
    url = urls.get(channel)
    return WebhookAdapter(url, {}) if url else None
