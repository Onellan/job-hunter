"""Application use cases for querying jobs and managing user workflow state."""

from __future__ import annotations

from uuid import UUID

from app.models.common import PaginatedResult, utc_now
from app.models.errors import EntityNotFoundError
from app.models.workspace import (
    BulkJobWorkflowResult,
    BulkJobWorkflowUpdate,
    JobWorkflowRecord,
    JobWorkflowUpdate,
    JobWorkspaceItem,
    JobWorkspaceQuery,
    WorkflowBulkAction,
)
from app.services.ports import JobWorkspaceRepository


class JobWorkspaceService:
    """Coordinate job-workspace reads and user state without SQL or HTML details."""

    def __init__(self, repository: JobWorkspaceRepository) -> None:
        """Create the workspace service with its query and state persistence port."""

        self._repository = repository

    def get(self, job_id: UUID) -> JobWorkspaceItem:
        """Return a detailed workspace job or raise a missing-resource error."""

        item = self._repository.get(job_id)
        if item is None:
            raise EntityNotFoundError("Job", job_id)
        return item

    def list(self, query: JobWorkspaceQuery) -> PaginatedResult[JobWorkspaceItem]:
        """Return a filtered and bounded workspace page."""

        return self._repository.list(query)

    def update_workflow(self, job_id: UUID, changes: JobWorkflowUpdate) -> JobWorkflowRecord:
        """Persist explicitly supplied bookmark, applied, or note state."""

        workflow = self._repository.update_workflow(job_id, changes, utc_now())
        if workflow is None:
            raise EntityNotFoundError("Job", job_id)
        return workflow

    def bulk_update_workflow(self, request: BulkJobWorkflowUpdate) -> BulkJobWorkflowResult:
        """Apply one reversible workflow action to at most one page of jobs."""

        changes = _changes_for_action(request.action)
        updated_count = self._repository.bulk_update_workflow(request.job_ids, changes, utc_now())
        return BulkJobWorkflowResult(updated_count=updated_count)


def _changes_for_action(action: WorkflowBulkAction) -> JobWorkflowUpdate:
    """Map an allow-listed bulk action to its explicit workflow update."""

    actions = {
        WorkflowBulkAction.BOOKMARK: JobWorkflowUpdate(is_bookmarked=True),
        WorkflowBulkAction.REMOVE_BOOKMARK: JobWorkflowUpdate(is_bookmarked=False),
        WorkflowBulkAction.MARK_APPLIED: JobWorkflowUpdate(is_applied=True),
        WorkflowBulkAction.CLEAR_APPLIED: JobWorkflowUpdate(is_applied=False),
    }
    return actions[action]
