# Release notes — 0.1.0

Job-Hunter 0.1.0 is the first local-first release candidate. It includes
provider-neutral job storage, bounded provider execution, workspace and
exports, schedules, direct and JobSpy adapters, explainable scoring, local
authentication, opt-in notifications, and private resume-derived matching.

Deploy as one FastAPI process with SQLite. On 1 GB hardware, configure TLS,
explicit trusted hosts, secure authenticated cookies, and a backup routine
before public exposure. Resume matching stores derived skills only, never
source resume text.

See [the release checklist](RELEASE.md) for target-device measurement, security
verification, backup/restore drilling, and reproducible release commands.
