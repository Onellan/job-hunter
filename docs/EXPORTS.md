# Export guide

Job-Hunter exports existing durable jobs; an export never triggers a provider
run or waits for scraping. Use the Jobs page to select up to 100 visible jobs,
choose CSV, JSON, or Excel, and download the selection. The SQLite backup link
creates a consistent copy of the entire file-backed database.

## Formats and memory use

| Format | Behaviour | Dependency |
|---|---|---|
| CSV | Streams rows immediately | Base package |
| JSON | Streams one JSON array item at a time | Base package |
| XLSX | Uses XlsxWriter constant-memory mode and a temporary file | `.[exports]` |
| SQLite | Uses SQLite's online backup API and a temporary file | File-backed SQLite only |

CSV and Excel cells are protected against spreadsheet formula injection from
untrusted provider text. JSON preserves the original text values. XLSX and
backup files are deleted after their download stream finishes; do not assume a
temporary file is retained as an archive.

## API

```text
GET /api/v1/exports/jobs?format=csv
GET /api/v1/exports/jobs?format=json&bookmarked=true
GET /api/v1/exports/jobs?format=xlsx&job_ids={job_id}
GET /api/v1/exports/sqlite
GET /api/v1/exports/events
```

Without `job_ids`, the jobs endpoint applies supplied workspace filters. With
`job_ids`, it exports only those selected jobs. The selected list is capped at
100 identifiers. Full filtered exports iterate in database batches rather than
loading all matching jobs into memory.

The **Export history** link beside the Jobs export controls opens a paginated
browser view of the same safe audit records. It displays only format, resource,
matching-job count, and UTC request time.

## Audit and privacy

Every export request creates one durable audit event. It records the format,
resource (`jobs` or `database`), matching job count when applicable, and UTC
timestamp. It does not store exported rows, job descriptions, notes, filter
text, output paths, or file bytes.

Job exports include private workflow notes because they are part of the
selected job workspace. This installation is currently unauthenticated and
workflow data is shared locally; export only from trusted deployments and do
not place credentials or other sensitive material in notes.
