"""Application-specific exception types."""


class ConfigurationError(ValueError):
    """Raised when the application configuration cannot be loaded safely."""
