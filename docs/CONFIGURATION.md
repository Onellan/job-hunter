# Configuration

## Authentication and notifications

See [authentication and notifications](AUTHENTICATION.md) for the local-account,
session, CSRF, rate-limit, and opt-in delivery configuration. Deployment secrets
must be supplied through an untracked configuration file or `JOB_HUNTER_`
environment variables.

## Resume matching

`resume.enabled` controls the local resume-derived skill profile. Set
`resume.skill_vocabulary` to additional deterministic terms and use
`resume.max_upload_characters` to bound accepted text. See
[private resume matching](MATCHING.md) for the privacy and retention model.

Job-Hunter reads `config/config.yaml` by default. Set
`JOB_HUNTER_CONFIG_FILE` to use a different file, such as an absolute path in
a container deployment. For example,
`JOB_HUNTER_CONFIG_FILE=config/local.yaml` selects an ignored local file.

The YAML file is validated at startup. Environment variables override YAML
values and use double underscores for nesting:

```text
JOB_HUNTER_DATABASE__URL=sqlite:///data/job-hunter.db
JOB_HUNTER_SERVER__PORT=8080
JOB_HUNTER_LOGGING__LEVEL=DEBUG
JOB_HUNTER_PROVIDER_EXECUTION__MAX_CONCURRENT_RUNS=1
JOB_HUNTER_SCHEDULER__RETRY_DELAY_SECONDS=60
JOB_HUNTER_SCORING__SKILLS='["python","sql"]'
```

## Settings

| Key | Purpose | Default |
|---|---|---|
| `app.name` | Application display name | `Job-Hunter` |
| `app.environment` | `development`, `testing`, or `production` | `development` |
| `app.debug` | Enables FastAPI debug mode | `false` |
| `server.host` | `job-hunter` entry-point bind host | `0.0.0.0` |
| `server.port` | `job-hunter` entry-point bind port | `8000` |
| `server.root_path` | Reverse-proxy path prefix | empty |
| `database.url` | SQLAlchemy database URL | SQLite file in `data/` |
| `database.echo` | Enables SQL statement logging | `false` |
| `logging.level` | Python logging threshold | `INFO` |
| `logging.json_logs` | Emits structured JSON logs | `true` |
| `provider_execution.max_concurrent_runs` | Provider worker threads | `1` (maximum `2`) |
| `provider_execution.max_queued_runs` | Waiting provider runs kept in memory | `4` (maximum `20`) |
| `scheduler.enabled` | Starts the in-process APScheduler adapter | `true` |
| `scheduler.retry_delay_seconds` | Delay before a bounded failed dispatch retry | `60` (5–3600) |
| `scheduler.max_registered_schedules` | Startup cap for persisted schedules | `100` (maximum `1000`) |
| `scoring.*` | Local deterministic match profile | disabled criteria by default |
| `authentication.enabled` | Enables the local login boundary | `false` |
| `authentication.session_cookie_secure` | Requires HTTPS-only session cookies | `false`; required in production |
| `authentication.login_*` | Bounded local failed-login protection | 5 attempts / 900 seconds |
| `notifications.*` | Explicit opt-in delivery adapters | disabled |
| `resume.*` | Local resume matching limits and vocabulary | enabled / 200000 characters |
| `security.trusted_hosts` | Accepted `Host` header values | localhost only |

For any network-facing installation, replace `security.trusted_hosts` with the
public DNS name handled by the reverse proxy. Do not place secrets in the
tracked configuration file; use environment variables or a deployment-specific
secret mechanism.

## Provider execution

Provider work runs outside HTTP request threads in a small, process-local
thread pool. The defaults permit one active run and four waiting runs. A run
submitted after this capacity is exhausted is saved as `failed` with the safe
`execution_capacity_exhausted` category; it is not silently discarded.

Keep `max_concurrent_runs` at `1` on a 1 GB Raspberry Pi unless measurement
shows a specific provider is safe at `2`. This setting controls local work
only: it is not a distributed queue and queued runs are lost on process exit
after being marked `cancelled` where possible. See [Providers](PROVIDERS.md)
for provider-specific configuration and installation.

## Scheduling

Scheduling uses one APScheduler dispatcher thread in the same application
process and calls the same saved-search service as the manual API. It never
scrapes while holding a database transaction; all provider work still flows
through `provider_execution` limits. Use exactly one application process per
SQLite database, otherwise each process would register the same durable
schedules. Set `scheduler.enabled: false` to disable dispatching while keeping
schedule definitions and history available through the API.

## Explainable scoring

`scoring` is a local deterministic profile: target roles, skills, salary,
workplace, experience, leadership, project-management, business-analysis, and
Agile preferences. Only configured preferences contribute to a job score, and
the score is recalculated on read without persisting job descriptions or user
profile data elsewhere. See [Explainable scoring](SCORING.md) for all settings
and its privacy boundary.

## Security baseline

Host validation, request correlation IDs, CSP, and conservative response
headers are enabled by default. When authentication is enabled, all resources
outside the small bootstrap/login boundary require an opaque session; unsafe
browser requests require CSRF validation. The login rate limit is process-local
and resets on restart, so it complements—not replaces—network controls at a
reverse proxy. Production configuration rejects local/wildcard trusted hosts
and insecure authenticated cookies.
