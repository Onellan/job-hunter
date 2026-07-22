# Configuration

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
| `security.trusted_hosts` | Accepted `Host` header values | localhost only |

For any network-facing installation, replace `security.trusted_hosts` with the
public DNS name handled by the reverse proxy. Do not place secrets in the
tracked configuration file; use environment variables or a deployment-specific
secret mechanism.

## Security baseline

Milestone 1 supplies host validation, request correlation IDs, and conservative
security headers. CSRF protection, password hashing, sessions, and
authorization will be implemented with the authentication milestone, when the
application first accepts authenticated state-changing browser requests.
