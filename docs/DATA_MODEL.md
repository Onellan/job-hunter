# Data Model

Milestone 2 establishes a provider-neutral schema. All application records use
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

## Retention and privacy

The base schema stores no raw provider payload or credentials. Job descriptions
may originate from public provider pages, but logs contain only safe identifiers
and counts. Retention automation is intentionally deferred until users can
configure a policy; do not delete job or run records implicitly.
