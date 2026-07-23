"""SQLite persistence for the local, resume-derived skill profile."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import ResumeProfileTable
from app.models.matching import ResumeProfile


class SqliteResumeRepository:
    """Store only the latest consented skill profile, never the source resume text."""

    def __init__(self, session: Session) -> None:
        """Create a request-scoped repository."""

        self._session = session

    def get(self) -> ResumeProfile | None:
        """Return the active profile, if a consented upload has occurred."""

        table = self._session.exec(select(ResumeProfileTable).limit(1)).first()
        return _to_profile(table) if table else None

    def replace(self, skills: list[str], now: datetime) -> ResumeProfile:
        """Replace derived skills in one short transaction and discard previous metadata."""

        for table in self._session.exec(select(ResumeProfileTable)).all():
            self._session.delete(table)
        table = ResumeProfileTable(skills=skills, consented_at=now, updated_at=now)
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return _to_profile(table)

    def delete(self) -> bool:
        """Delete locally derived skills and revoke the retained consent record."""

        table = self._session.exec(select(ResumeProfileTable).limit(1)).first()
        if table is None:
            return False
        self._session.delete(table)
        commit_or_raise_conflict(self._session)
        return True


def _to_profile(table: ResumeProfileTable) -> ResumeProfile:
    """Convert a table without retaining or exposing resume source text."""

    return ResumeProfile(
        id=table.id,
        skills=table.skills,
        consented_at=table.consented_at,
        consent_version=table.consent_version,
        updated_at=table.updated_at,
    )
