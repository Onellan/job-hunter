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
supports source, workplace, bookmarked, and applied filters. Choose one of four
allow-listed sort orders: recently seen, recently published, title, or company.
Results use bounded offset pagination with a maximum of 100 rows per request.

Open a job to read its provider description, salary, direct application link,
and standard source metadata. Provider-specific technologies, benefits, and AI
matching are intentionally not invented; explainable scoring is added in a
later milestone.

## Track your workflow

Select jobs to bookmark, remove bookmarks, mark applied, or clear applied.
Each action changes at most 100 selected jobs. On the job detail page, add a
private note alongside single-job bookmark and applied controls.

Workflow state is local to this installation and is currently shared by every
browser user because authentication has not yet been introduced. Do not store
credentials or sensitive personal information in notes. CSRF protection and
per-user ownership will be added with the authentication milestone; do not
expose this unauthenticated application to untrusted users.

## Progressive enhancement

HTMX refreshes result tables and workflow panels without a full page reload.
If JavaScript is unavailable, filters, bulk actions, bookmarks, applied state,
and notes still submit as regular HTML forms and redirect to a usable page.
