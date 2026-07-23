"""Versioned local-only resume skill profile endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_resume_matching_service
from app.models.matching import ResumeProfile, ResumeUploadRequest
from app.services.matching import ResumeMatchingService

router = APIRouter(prefix="/resume-profile", tags=["resume matching"])


@router.get("", response_model=ResumeProfile)
def get_resume_profile(
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> ResumeProfile:
    """Return the current consented derived-skill profile, never source resume text."""

    return service.get_profile()


@router.put("", response_model=ResumeProfile)
def upload_resume_profile(
    request: ResumeUploadRequest,
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> ResumeProfile:
    """Extract skills from explicitly consented UTF-8 text and discard the submitted text."""

    return service.upload(request)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume_profile(
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> Response:
    """Permanently delete the consented derived-skill profile."""

    service.delete_profile()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
