"""Local authentication contracts without exposing password material."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

Username = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_.-]{3,64}$")]
Password = Annotated[str, StringConstraints(min_length=12, max_length=256)]


class Credentials(BaseModel):
    """Validated credentials accepted only at bootstrap and login boundaries."""

    username: Username
    password: Password


class UserRecord(BaseModel):
    """Safe persisted user information, excluding the password verifier."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    username: Username
    created_at: datetime


class AuthenticatedSession(BaseModel):
    """Authenticated session details held only for the active request."""

    user: UserRecord
    csrf_token: str
