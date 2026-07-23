"""Provider-neutral application error types."""

from __future__ import annotations

from uuid import UUID


class EntityNotFoundError(LookupError):
    """Raised when a requested durable entity does not exist."""

    def __init__(self, entity_name: str, entity_id: UUID) -> None:
        """Create an error with safe entity context.

        Args:
            entity_name: Human-readable entity category.
            entity_id: Identifier that could not be resolved.
        """

        super().__init__(f"{entity_name} was not found: {entity_id}")
        self.entity_name = entity_name
        self.entity_id = entity_id


class ResourceConflictError(ValueError):
    """Raised when an operation conflicts with durable application state."""


class ResourceValidationError(ValueError):
    """Raised when a requested operation is valid syntactically but unavailable."""


class NoEnabledProviderError(ResourceConflictError):
    """Raised when a saved search has no enabled configured provider to run."""


class ProviderRunTransitionError(ResourceConflictError):
    """Raised when a provider run is moved through an invalid state transition."""
