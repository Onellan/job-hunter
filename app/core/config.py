"""Validated YAML and environment-based application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.core.errors import ConfigurationError


class ApplicationSettings(BaseModel):
    """Settings that identify the running application."""

    name: str = "Job-Hunter"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    version: str = "0.1.0"


class ServerSettings(BaseModel):
    """HTTP server settings."""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    root_path: str = ""


class DatabaseSettings(BaseModel):
    """Database connection settings."""

    url: str = "sqlite:///data/job-hunter.db"
    echo: bool = False


class LoggingSettings(BaseModel):
    """Structured logging settings."""

    level: str = "INFO"
    json_logs: bool = True


class SecuritySettings(BaseModel):
    """Baseline HTTP security settings."""

    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])


class Settings(BaseSettings):
    """The complete validated application configuration.

    Values are loaded from YAML first and can be overridden using nested
    environment variables such as ``JOB_HUNTER_DATABASE__URL``.
    """

    model_config = SettingsConfigDict(
        env_prefix="JOB_HUNTER_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Ensure environment variables take precedence over YAML values."""

        return env_settings, init_settings, dotenv_settings, file_secret_settings

    @classmethod
    def from_yaml(cls, config_path: Path) -> Settings:
        """Load validated settings from a YAML file.

        Args:
            config_path: The YAML file containing the baseline configuration.

        Raises:
            ConfigurationError: If the file is missing, malformed, or does not
                contain a mapping at its root.
        """

        if not config_path.is_file():
            message = f"Configuration file does not exist: {config_path}"
            raise ConfigurationError(message)

        try:
            loaded_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exception:
            message = f"Configuration file is not valid YAML: {config_path}"
            raise ConfigurationError(message) from exception

        if loaded_config is None:
            loaded_config = {}
        if not isinstance(loaded_config, dict):
            message = f"Configuration file must contain a mapping: {config_path}"
            raise ConfigurationError(message)

        return cls(**loaded_config)


@lru_cache(maxsize=4)
def get_settings(config_path: Path | None = None) -> Settings:
    """Return cached application settings from the configured YAML file."""

    selected_path = config_path or Path(os.getenv("JOB_HUNTER_CONFIG_FILE", "config/config.yaml"))
    return Settings.from_yaml(selected_path)
