# Data Model

Milestone 6 establishes a provider-neutral schema plus small user workflow,
export audit, and scheduler state. All application records use
UUID primary keys; all timestamps are exposed as UTC ISO-8601 values.

## Jobs

`jobs` is the canonical listing table. It contains source metadata, title,
company, location, workplace and employment type, description, normalised
salary, publication date, and discovery timestamps.

Identity is deliberate and idempotent:

1. `source` + `source_job_id` is used when the source supplies a stable ID.
2. Otherwise, a canonical `source_url` is used.
3. Otherwise, a SHA-256 fingerprint of normalised title, company, location,
   and publication date is used.

The first known source remains the canonical source for a deduplicated job.
Later observations refresh content and `last_seen_at` without creating another
row. This keeps one durable record while avoiding a multi-source join model
before it is needed.

Indexes support source and date filtering, newest-first result pages, workplace
filtering, and identity lookup. Salary values are decimal amounts paired with a
three-letter currency and period; an amount is rejected without both.

## Providers

`providers` stores a provider code, display name, enablement flag, and
non-secret JSON configuration. It does not contain provider code, credentials,
cookies, or browser profiles. Provider implementations arrive in Milestone 3.

## Saved searches

`searches` stores a name, enablement state, and provider-neutral criteria JSON:
keywords, Boolean query, exclusions, locations, remote preference, salary,
experience, posting age, provider codes, and company include/exclude lists.
The database stores a definition only; executing it is a later provider-platform
responsibility.

## Provider runs

`provider_runs` preserves the outcome of one provider invocation and optionally
links it to a saved search. Valid status transitions are:

```text
pending → running → succeeded | failed | cancelled
pending → cancelled
```

Starting and terminal transitions set timestamps automatically. A provider with
run history cannot be deleted. Deleting a saved search retains its historical
runs but sets their `search_id` to `NULL`.

## Job workflow state

`job_workflows` is an optional one-to-one record keyed by `job_id`. It stores
only user-managed `is_bookmarked`, `is_applied`, and `notes` values, plus audit
timestamps. A row is created lazily on the first workflow action, so collected
jobs without user interaction consume no additional workflow row.

The row is deleted with its job through a foreign key. Bookmark and applied
indexes support the workspace's SQLite-side filters; composite state/update
indexes support future activity views without keeping an in-memory job cache.
Workflow state never changes a job's provider identity, description, salary, or
other source-owned content.

## Export audit events

`export_events` records that a user requested a jobs or database export. Each
row contains a UUID, format, resource category, selected or matched job count,
and timestamp. It deliberately excludes job descriptions, notes, raw filters,
file paths, and the exported bytes. Indexes support newest-first operator audit
history without retaining a copy of sensitive export content.

## Schedules and schedule runs

`schedules` links a saved search to either a daily UTC time or a five-field
cron expression. It also stores enablement, incremental-run metadata, an
explicit retry cap, and the latest successful dispatch timestamp. A search with
an active schedule cannot be deleted accidentally; remove the schedule first.

`schedule_runs` is compact dispatch history. It records whether provider work
was queued or dispatch failed, the retry attempt, manual versus timed source,
counts, safe error category, and timestamps. It intentionally does not copy
provider result data: `provider_runs` remains the detailed execution history.
Deleting a schedule retains this history with a null schedule reference.

## Local authentication and notification deliveries

`users` contains the single local username, salted password verifier, and
creation timestamp. `sessions` links that user to a SHA-256 digest of the
opaque session and CSRF values plus an expiry. Raw credentials and tokens never
enter the database.

`notification_deliveries` is an intentionally payload-free audit table. It
contains the channel, event category, delivery result, safe error category, and
timestamps. It does not retain message contents, recipient identifiers,
webhooks, SMTP URLs, or bot tokens. An index supports newest-first history.

## Resume-derived skills

`resume_profiles` stores the latest explicitly consented list of extracted
skills, a consent timestamp/version, and an update timestamp. It deliberately
does not store raw resume text, uploaded files, names, MIME types, or hashes.
Job comparison results are calculated from current job data and this profile on
demand, and are not persisted.

## Retention and privacy

The base schema stores no raw provider payload or credentials. Job descriptions
may originate from public provider pages, but logs contain only safe identifiers
and counts. Retention automation is intentionally deferred until users can
configure a policy; do not delete job or run records implicitly.
