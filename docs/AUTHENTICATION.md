# Authentication and notifications

## Local authentication

Authentication is disabled in the development baseline and is enabled in the
production example configuration. Before making the application reachable by
untrusted clients, run the Alembic migrations, set `authentication.enabled` to
`true`, use HTTPS, and set `authentication.session_cookie_secure` to `true`.
The settings validator rejects an enabled production configuration that omits
secure session cookies.

Open `/login` to create the single local account, then sign in. Passwords are
stored only as salted `scrypt` verifiers. Browser sessions and CSRF values are
random opaque values; only their SHA-256 digests are stored. Sessions expire
after `authentication.session_ttl_hours` and can be invalidated by logging out.

All browser and API resources except health, static files, and the bootstrap or
login boundaries require a session when authentication is enabled. Unsafe
browser requests require the `csrf_token` form field or `X-CSRF-Token` header.
The login endpoint also uses a bounded in-process failed-attempt limiter. It is
intentionally local and resets after a restart, keeping this SQLite-first
deployment free of another service.

The browser login page preserves only the submitted username on a validation,
credential, or rate-limit failure; passwords are never rendered back. Once an
owner exists, first-time setup is hidden. Authenticated pages show the account
name and a CSRF-protected **Sign out** control that invalidates the server-side
session and clears both browser cookies.

## Notifications

Notifications are disabled unless `notifications.enabled` is `true`. Configure
only the channels you intend to use through a deployment-specific YAML file or
`JOB_HUNTER_NOTIFICATIONS__...` environment variables. Never commit SMTP URLs,
webhooks, bot tokens, or recipient identifiers.

Supported channels are SMTP email, Telegram, Slack, and Teams. Use
`POST /api/v1/notifications/test` with `{"channel":"slack"}` (or another
channel) to verify an enabled channel. `GET /api/v1/notifications/deliveries`
returns a paginated audit history. The history stores channel, event type,
outcome, error category, and timestamps only; it never retains recipients,
payloads, credentials, or webhook URLs.

The browser **Activity** page links to the same paginated notification-history
metadata. It has no notification test form and never exposes recipients,
messages, configured values, or secrets.

For email, `notifications.email_url` uses an SMTP URL such as
`smtps://user:password@mail.example.com?from=jobs@example.com&to=you@example.com`.
Encode URL-special characters in credentials. Telegram requires both
`telegram_bot_token` and `telegram_chat_id`; Slack and Teams each use their
respective webhook URL. These values are secrets and examples are deliberately
not placed in tracked configuration.
