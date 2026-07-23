# Workspace guide

The Job-Hunter workspace is a fast, server-rendered view over jobs already
stored by provider runs. Open `/dashboard` for a small operational summary and
`/jobs` to browse opportunities.

## Dashboard

The dashboard shows jobs found today, the most recent completed provider run,
enabled provider count, provider-run failures created today, recent saved
searches, and the five latest jobs. Its summary refreshes every 30 seconds with
HTMX; it does not poll provider portals or start background work.

## Find and review jobs

The Jobs page filters title, company, and location text in SQLite. It also
supports source, workplace, exact employment type, publication age (one to 30
days), bookmarked, and applied filters. Choose one of four
allow-listed sort orders: recently seen, recently published, title, or company.
Results use bounded offset pagination with a maximum of 100 rows per request.

Open a job to read its provider description, salary, direct application link,
and standard source metadata. Provider-specific technologies, benefits, and AI
matching are intentionally not invented; explainable scoring is added in a
later milestone.

## Track your workflow

Select jobs to bookmark, remove bookmarks, mark applied, clear applied, or
compare two or three jobs against the consented resume profile. Each workflow
action changes at most 100 selected jobs. On the job detail page, add a private
note alongside single-job bookmark and applied controls.

Workflow state is local to this installation. When authentication is enabled,
browser changes require the local session and a CSRF token. Do not store
credentials or sensitive personal information in notes; do not expose a local
deployment to untrusted users.

## Feedback and recovery

Browser forms announce validation and successful resume-skill extraction in a
small live region. Browser-side 4xx and unexpected 5xx failures render a safe
HTML response with a request reference rather than raw API JSON. The versioned
`/api/v1` endpoints continue to return JSON errors for API clients.

## Progressive enhancement

HTMX refreshes result tables and workflow panels without a full page reload.
If JavaScript is unavailable, filters, bulk actions, bookmarks, applied state,
and notes still submit as regular HTML forms and redirect to a usable page.
