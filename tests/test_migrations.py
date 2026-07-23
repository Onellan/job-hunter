"""Tests for the explicit Alembic schema migration workflow."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migrations_create_expected_workspace_schema(tmp_path: Path) -> None:
    """The versioned migrations create the durable workspace tables and indexes."""

    database_path = tmp_path / "migrated.db"
    configuration = Config(str(Path("alembic.ini").resolve()))
    configuration.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(configuration, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        job_indexes = {index["name"] for index in inspector.get_indexes("jobs")}
    finally:
        engine.dispose()

    assert {
        "alembic_version",
        "export_events",
        "job_workflows",
        "jobs",
        "notification_deliveries",
        "provider_runs",
        "providers",
        "resume_profiles",
        "schedule_runs",
        "schedules",
        "sessions",
        "searches",
        "users",
    } <= table_names
    assert {"ix_jobs_source", "ix_jobs_last_seen_at", "ix_jobs_source_published_at"} <= job_indexes
