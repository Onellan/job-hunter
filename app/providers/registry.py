"""Automatic discovery and construction of provider plugin classes."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from importlib import metadata

from app.providers.base import BaseProvider
from app.providers.errors import ProviderRegistrationError

_ENTRY_POINT_GROUP = "job_hunter.providers"


class ProviderRegistry:
    """Discover provider classes without coupling services to implementations."""

    def __init__(self, provider_types: Iterable[type[BaseProvider]]) -> None:
        """Validate and index provider classes by their stable code."""

        self._provider_types: dict[str, type[BaseProvider]] = {}
        for provider_type in provider_types:
            self._register(provider_type)

    @classmethod
    def discover(cls) -> ProviderRegistry:
        """Discover built-in modules and external entry-point provider plugins."""

        _import_builtin_provider_modules()
        provider_types = set(_all_subclasses(BaseProvider))
        provider_types.update(_load_entry_point_providers())
        return cls(provider_types)

    @property
    def codes(self) -> frozenset[str]:
        """Return the immutable set of registered provider codes."""

        return frozenset(self._provider_types)

    def create(self, code: str) -> BaseProvider:
        """Construct a provider by configuration code.

        Raises:
            ProviderRegistrationError: If no provider implementation is registered.
        """

        provider_type = self._provider_types.get(code)
        if provider_type is None:
            message = f"No provider plugin is registered for code: {code}"
            raise ProviderRegistrationError(message)
        return provider_type()

    def _register(self, provider_type: type[BaseProvider]) -> None:
        """Validate one plugin class and reject ambiguous provider codes."""

        code = getattr(provider_type, "code", "")
        display_name = getattr(provider_type, "display_name", "")
        if not isinstance(code, str) or not code:
            raise ProviderRegistrationError("Provider plugins require a non-empty code")
        if not isinstance(display_name, str) or not display_name:
            raise ProviderRegistrationError(f"Provider plugin {code} requires a display name")
        if code in self._provider_types:
            raise ProviderRegistrationError(f"Provider plugin code is duplicated: {code}")
        self._provider_types[code] = provider_type


def _import_builtin_provider_modules() -> None:
    """Import all modules in the local provider package for subclass discovery."""

    provider_package = importlib.import_module("app.providers")
    for module in pkgutil.iter_modules(provider_package.__path__, f"{provider_package.__name__}."):
        importlib.import_module(module.name)


def _load_entry_point_providers() -> set[type[BaseProvider]]:
    """Load optional external plugins registered through Python entry points."""

    entry_points = metadata.entry_points()
    selected_entry_points = entry_points.select(group=_ENTRY_POINT_GROUP)
    provider_types: set[type[BaseProvider]] = set()
    for entry_point in selected_entry_points:
        loaded_provider = entry_point.load()
        if not isinstance(loaded_provider, type) or not issubclass(loaded_provider, BaseProvider):
            message = f"Entry point {entry_point.name} is not a BaseProvider class"
            raise ProviderRegistrationError(message)
        provider_types.add(loaded_provider)
    return provider_types


def _all_subclasses(provider_type: type[object]) -> set[type[BaseProvider]]:
    """Return recursively discovered subclasses of a provider base class."""

    direct_subclasses = set(provider_type.__subclasses__())
    provider_subclasses = {
        subclass for subclass in direct_subclasses if issubclass(subclass, BaseProvider)
    }
    return provider_subclasses | {
        nested_provider
        for subclass in provider_subclasses
        for nested_provider in _all_subclasses(subclass)
    }
