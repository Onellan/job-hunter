"""Job-workflow and query contracts used by the search workspace."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.job import EmploymentType, JobRecord, ProviderCode, WorkplaceType


class JobSort(StrEnum):
    """The inexpensive indexed orderings available in the job workspace."""

    RECENT = "recent"
    PUBLISHED = "published"
    TITLE = "title"
    COMPANY = "company"


class JobWorkspaceQuery(BaseModel):
    """Validated filters and pagination for a bounded job-workspace query."""

    text: str | None = Field(default=None, min_length=1, max_length=200)
    source: ProviderCode | None = None
    workplace_type: WorkplaceType | None = None
    location: str | None = Field(default=None, min_length=1, max_length=300)
    employment_type: EmploymentType | None = None
    posted_within_days: int | None = Field(default=None, ge=1, le=30)
    bookmarked: bool | None = None
    applied: bool | None = None
    sort: JobSort = JobSort.RECENT
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=100)


class JobWorkflowState(BaseModel):
    """User-managed state attached to a job without changing provider data."""

    model_config = ConfigDict(frozen=True)

    is_bookmarked: bool = False
    is_applied: bool = False
    notes: str | None = None


class JobWorkflowRecord(JobWorkflowState):
    """A persisted job-workflow state record."""

    job_id: UUID
    created_at: datetime
    updated_at: datetime


class JobWorkflowUpdate(BaseModel):
    """An explicit change to user-managed job workflow state."""

    is_bookmarked: bool | None = None
    is_applied: bool | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def validate_change(self) -> JobWorkflowUpdate:
        """Reject empty updates that would hide a client-side form error."""

        if not self.model_fields_set:
            raise ValueError("At least one workflow field must be supplied")
        if "notes" in self.model_fields_set and self.notes is not None:
            self.notes = self.notes.strip() or None
        return self


class WorkflowBulkAction(StrEnum):
    """The safe reversible workflow changes available for selected jobs."""

    BOOKMARK = "bookmark"
    REMOVE_BOOKMARK = "remove_bookmark"
    MARK_APPLIED = "mark_applied"
    CLEAR_APPLIED = "clear_applied"


class BulkJobWorkflowUpdate(BaseModel):
    """A bounded bulk workflow command for existing jobs."""

    job_ids: list[UUID] = Field(min_length=1, max_length=100)
    action: WorkflowBulkAction


class BulkJobWorkflowResult(BaseModel):
    """The number of durable job workflow records updated by a bulk command."""

    updated_count: int = Field(ge=0)


class JobWorkspaceItem(BaseModel):
    """A job paired with its lazily-created user workflow state."""

    model_config = ConfigDict(frozen=True)

    job: JobRecord
    workflow: JobWorkflowState
