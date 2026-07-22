# Database Migrations

Job-Hunter uses Alembic for explicit, versioned schema changes. Production code
does not create tables automatically.

## Apply migrations

Back up the SQLite database, then apply all migrations:

```powershell
Copy-Item data/job-hunter.db data/job-hunter.db.backup
python -m alembic upgrade head
```

The Alembic environment reads `database.url` from the normal validated
configuration. Set `JOB_HUNTER_CONFIG_FILE` or
`JOB_HUNTER_DATABASE__URL` before running the command when needed.

Docker Compose applies `upgrade head` in its entry point before starting
Job-Hunter. Run one deployment instance per SQLite database while upgrading.

## Create a migration

After changing SQLModel tables, generate a reviewed migration:

```powershell
python -m alembic revision --autogenerate -m "describe schema change"
```

Review the generated file under `migrations/versions/`, add appropriate indexes
and data migration steps, then test against a fresh SQLite database and a copy
of representative data. Never rely on `create_all()` or edit an already
released migration.

## Rollback

Only run a downgrade after verifying its data-loss implications and restoring a
backup plan:

```powershell
python -m alembic downgrade -1
```

For destructive migrations, document a restoration procedure rather than
assuming a downgrade can reconstruct data.
