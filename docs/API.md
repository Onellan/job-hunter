# API Reference

All JSON resources below are relative to `/api/v1`; for example, health is
`GET /api/v1/health`. OpenAPI is available at `/docs` while the application is
running. Responses use UUID IDs and UTC timestamps.

## Pagination

Collection endpoints use bounded offset pagination:

```text
?offset=0&limit=25
```

`limit` is between 1 and 100. A response has `items`, `total`, `offset`, and
`limit`. Jobs also accept an optional `source` filter; provider runs accept
optional `provider_id` and `search_id` filters.

## Resources

| Resource | Endpoints |
|---|---|
| Health | `GET /health` |
| Dashboard | `GET /dashboard` |
| Jobs | `POST/GET /jobs`, `GET/PATCH/DELETE /jobs/{id}` |
| Job scoring | `GET /jobs/{id}/score` |
| Job workspace | `GET /jobs/workspace`, `GET /jobs/{id}/workspace`, `PATCH /jobs/{id}/workflow`, `POST /jobs/workflow/bulk` |
| Exports | `GET /exports/jobs`, `GET /exports/sqlite`, `GET /exports/events` |
| Providers | `POST/GET /providers`, `GET/PATCH/DELETE /providers/{id}` |
| Searches | `POST/GET /searches`, `GET/PATCH/DELETE /searches/{id}`, `POST /searches/{id}/run` |
| Schedules | `POST/GET /schedules`, `GET/PATCH/DELETE /schedules/{id}`, `POST /schedules/{id}/run`, `GET /schedules/{id}/runs` |
| Provider runs | `POST/GET /provider-runs`, `GET/PATCH/DELETE /provider-runs/{id}` |

`POST /jobs` is an idempotent upsert. It returns `201` with `created: true` for
a new durable job and `200` with `created: false` when the identity hierarchy
matches a known job.

Provider-run creation requires an existing provider and, when supplied, an
existing saved search. Lifecycle conflicts return `409`; missing durable
resources return `404`; malformed request data returns `422`.

## Examples

Create a provider registration:

```json
{
  "code": "jobspy",
  "display_name": "JobSpy",
  "enabled": true,
  "configuration": {"sites": ["indeed"], "results_wanted": 25}
}
```

Create a saved search:

```json
{
  "name": "Remote Python roles",
  "criteria": {
    "keywords": ["python"],
    "remote_preference": "remote",
    "excluded_keywords": ["intern"]
  }
}
```

Start a saved search without blocking the request:

```text
POST /api/v1/searches/{search_id}/run
```

The endpoint returns `202 Accepted` with one durable provider-run record per
eligible enabled provider. Poll `GET /provider-runs/{run_id}` for each result.
When a saved search names provider codes, unavailable or disabled codes appear
in `skipped_provider_codes`. If none of the requested providers are enabled,
the endpoint returns `409` and creates no runs.

Each run is independent: a provider failure is recorded on that run and does
not stop other configured providers. The endpoint only queues work; it never
scrapes within the request handler.

## Schedules

Schedules attach a daily UTC time or a standard five-field cron expression to
an existing saved search. Creating or updating one immediately synchronises its
in-process APScheduler trigger. A manual dispatch is asynchronous:

```json
POST /api/v1/schedules
{
  "name": "Morning Python roles",
  "search_id": "...",
  "trigger_type": "daily",
  "daily_time": "08:30:00",
  "incremental": true,
  "retry_limit": 1
}
```

```text
POST /api/v1/schedules/{schedule_id}/run
GET /api/v1/schedules/{schedule_id}/runs
```

The run endpoint returns `202 Accepted`. History records dispatch attempts and
the number of provider runs queued; provider outcomes remain available through
`/provider-runs`. Retry attempts are capped by `retry_limit` and apply when a
dispatch cannot queue any provider work.

## Workspace queries and workflow state

`GET /jobs/workspace` returns jobs paired with their user-managed workflow
state. It accepts `text`, `source`, `workplace_type`, `bookmarked`, `applied`,
`sort` (`recent`, `published`, `title`, or `company`), `offset`, and `limit`.
The query is bounded to 100 records and performs filtering in SQLite.

Update one job's bookmark, application, or note state without changing its
provider data:

```json
PATCH /api/v1/jobs/{job_id}/workflow
{
  "is_bookmarked": true,
  "is_applied": false,
  "notes": "Ask about team structure."
}
```

Apply a reversible bulk action to up to 100 selected jobs:

```json
POST /api/v1/jobs/workflow/bulk
{
  "job_ids": ["..."],
  "action": "mark_applied"
}
```

Valid actions are `bookmark`, `remove_bookmark`, `mark_applied`, and
`clear_applied`. `GET /dashboard` returns compact metrics, recent searches,
and the five latest jobs for non-browser clients.

## Exports

Download filtered jobs with `GET /exports/jobs?format=csv`, `json`, or `xlsx`.
It accepts the workspace filters (`text`, `source`, `workplace_type`,
`bookmarked`, `applied`, and `sort`). Supplying one or more `job_ids` exports
that explicit selection instead; the selection is limited to 100 IDs.

```text
GET /api/v1/exports/jobs?format=csv&job_ids={job_id}
GET /api/v1/exports/sqlite
GET /api/v1/exports/events?offset=0&limit=25
```

CSV and JSON responses are streamed. XLSX responses use a temporary
constant-memory workbook and require the `exports` optional dependency group.
SQLite backup is available only for a file-backed SQLite configuration. Each
request creates a small audit event containing only format, resource, count,
and timestamp; it does not retain exported job content or filter text.

## Local authentication and notifications

When `authentication.enabled` is true, browser and API resources require an
opaque local session except health, static assets, and bootstrap/login. Create
the single account with `POST /api/v1/auth/bootstrap`, then exchange
credentials at `POST /api/v1/auth/login`. The successful response sets the
HttpOnly session cookie and readable CSRF cookie; browser writes submit the
CSRF value as `csrf_token` or `X-CSRF-Token`. `POST /api/v1/auth/logout`
invalidates the session.

Notifications are opt-in. Verify a configured channel and view its safe audit
history through:

```text
POST /api/v1/notifications/test
GET /api/v1/notifications/deliveries?offset=0&limit=25
```

The test request contains only `{"channel":"email|telegram|slack|teams"}`.
Delivery history never returns recipients, message text, or credentials.

## Private resume matching

`PUT /api/v1/resume-profile` accepts explicitly consented UTF-8 text as
`{"consent":true,"content":"..."}`. The submitted source text is not
stored. `GET` returns only the derived skills and consent metadata; `DELETE`
removes it. Compare two or three existing jobs without persisting the result:

```text
POST /api/v1/jobs/compare
```

The request body is `{"job_ids":["...", "..."]}`. See
[private resume matching](MATCHING.md) for retention and text-only limits.
