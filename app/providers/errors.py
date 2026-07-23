"""Expected provider-boundary failures with safe user-facing classifications."""

from __future__ import annotations


class ProviderError(RuntimeError):
    """A safe, expected failure while configuring or executing a provider."""

    category = "provider_error"
    summary = "The provider could not complete this search."


class ProviderDependencyError(ProviderError):
    """Raised when an optional provider dependency is not installed."""

    category = "dependency_unavailable"
    summary = "The provider dependency is not installed."


class ProviderConfigurationError(ProviderError):
    """Raised when provider or search settings cannot be translated safely."""

    category = "invalid_configuration"
    summary = "The provider configuration is invalid for this search."


class ProviderExecutionError(ProviderError):
    """Raised when a provider cannot retrieve its source data."""

    category = "provider_execution_failed"
    summary = "The provider could not retrieve jobs from its source."


class ProviderRateLimitError(ProviderExecutionError):
    """Raised when a provider source rejects the configured request rate."""

    category = "provider_rate_limited"
    summary = "The provider temporarily limited this search."


class ProviderTimeoutError(ProviderExecutionError):
    """Raised when a provider source does not respond within its configured timeout."""

    category = "provider_timeout"
    summary = "The provider did not respond before the configured timeout."


class ProviderParsingError(ProviderError):
    """Raised when provider output cannot yield a valid standard job."""

    category = "provider_parsing_failed"
    summary = "The provider returned data that could not be processed."


class ProviderRegistrationError(ProviderError):
    """Raised when provider discovery finds an invalid or duplicate plugin."""

    category = "provider_registration_failed"
    summary = "The provider plugin registration is invalid."
