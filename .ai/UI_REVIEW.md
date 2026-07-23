# Job-Hunter UI Review — 2026-07-23

## Docker runtime

- **Result:** Started successfully with the documented Compose workflow.
- **URL:** `http://127.0.0.1:8000`
- **Container:** `job-hunter-job-hunter-1`, one application container, healthy.
- **Health:** `GET /api/v1/health` returned HTTP 200; migrations completed and the
  in-process scheduler started. SQLite data is bind-mounted at `./data`; config
  is read-only at `./config`.

## Routes and workflows reviewed

Runtime browser review covered `/dashboard`, `/jobs`, `/matching`, and `/login`,
including empty states, direct route access, page titles, form labels, the
390 × 844, 768 × 1024, and 1366 × 768 viewports, and a Jobs filter submission.
The dashboard is a clear compact status view, Jobs has understandable filter
labels and an empty state, and Matching clearly explains its privacy boundary.

The browser submission of untouched Jobs filters failed with a raw HTTP 422
JSON response. Every reviewed route also emitted an HTMX/CSP console error.
At 390 × 844, the matching page had document-level horizontal overflow and the
header navigation was clipped. `/matching` additionally requires manual job
UUID entry for comparison.

## Inventory findings

The browser exposes Dashboard, Jobs, Matching, Login, workflow actions, and
exports. Provider management, saved searches/manual runs, schedules/history,
provider runs, notification history, and export audit history are API-only and
unreachable from navigation. There is no browser logout/account affordance.

## Accessibility and Raspberry Pi findings

Reviewed pages have semantic headings, labelled fields, a skip link, table
headers, and ARIA live targets. Keyboard traversal, contrast, screen-reader
output, and dialog behavior require a manual audit. The UI remains
server-rendered with small HTMX fragments, bounded pagination, and a 30-second
dashboard refresh; no recommendation adds a heavy framework or high-frequency
polling.

## Limitations

No external providers were scraped and no test jobs, credentials, schedules, or
notifications were created. Provider, scheduler, and run workflows could not
be exercised because they have no UI. Browser review used local Docker runtime;
it is not Raspberry Pi performance evidence.

## Highest-priority UI tasks added

1. UI-001 — blank job filters return 422 JSON.
2. UI-002 — CSP conflicts with HTMX.
3. UI-003 — saved-search create/run workflow.
4. UI-004 — provider management UI.
5. UI-005 — schedules and dispatch history UI.
6. UI-006 — provider/schedule operations view.
7. UI-007 — mobile navigation horizontal overflow.
8. UI-008 — account/logout and login feedback.
9. UI-009 — selected-job comparison.
10. UI-010 — required search filters and reset control.
