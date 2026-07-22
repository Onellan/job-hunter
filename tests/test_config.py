"""Tests for validated configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import ConfigurationError


def test_environment_values_override_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested environment settings take precedence over the YAML baseline."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text("server:\n  port: 8000\n", encoding="utf-8")
    monkeypatch.setenv("JOB_HUNTER_SERVER__PORT", "8100")

    settings = Settings.from_yaml(config_path)

    assert settings.server.port == 8100


def test_missing_yaml_configuration_is_rejected(tmp_path: Path) -> None:
    """Configuration loading produces a useful domain-specific error."""

    with pytest.raises(ConfigurationError, match="does not exist"):
        Settings.from_yaml(tmp_path / "missing.yaml")
