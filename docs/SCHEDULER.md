# Scheduler

Milestone 6 provides local, durable saved-search scheduling without a queue,
worker service, or second deployment. APScheduler is an in-process adapter:
it reads persisted definitions at startup and calls the same application
service used by the manual search API.

## Create a schedule

Create schedules through `/api/v1/schedules`. A schedule uses exactly one of:

- `trigger_type: "daily"` with `daily_time` in UTC, for example `"08:30:00"`.
- `trigger_type: "cron"` with a standard five-field cron expression, for
  example `"0 8 * * 1-5"`.

`incremental` is enabled by default. Incremental state is durable through the
last-dispatch timestamp and existing idempotent job identity rules, so repeated
runs refresh known jobs rather than create duplicates. Providers may use the
saved posting-age criteria to reduce source-side lookback.

## Operations and limits

Run one Job-Hunter process per SQLite database. Multiple processes register
the same persisted schedules and would issue duplicate work. The scheduler has
one dispatcher thread; every provider run then enters the existing bounded
local executor. This preserves the Raspberry Pi memory and CPU limits.

Each dispatch creates a small `schedule_runs` history record before it queues
any providers. A failed dispatch, or one where every provider was rejected by
the bounded queue, is retried after `scheduler.retry_delay_seconds` until its
schedule's `retry_limit` is exhausted (0–3). Provider execution outcomes stay
in `provider_runs`; a failed portal does not block other providers.

`POST /api/v1/schedules/{id}/run` queues an immediate manual schedule dispatch
and returns `202`. Review its dispatch history at
`GET /api/v1/schedules/{id}/runs`, then inspect the referenced provider runs
for completion details.

Set `scheduler.enabled: false` to suppress timed and manual dispatching during
maintenance. Definitions and history remain durable.
