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
| Jobs | `POST/GET /jobs`, `GET/PATCH/DELETE /jobs/{id}` |
| Providers | `POST/GET /providers`, `GET/PATCH/DELETE /providers/{id}` |
| Searches | `POST/GET /searches`, `GET/PATCH/DELETE /searches/{id}` |
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
  "configuration": {"result_limit": 25}
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

These resources persist configuration and run state only. They do not invoke a
provider synchronously; execution is added in Milestone 3.
