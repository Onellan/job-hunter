"""Release-safety checks for the lightweight container and package defaults."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_container_entrypoint_does_not_shadow_application_console_script() -> None:
    """The migration wrapper has a distinct name and delegates to the installed command."""

    dockerfile = Path("docker/Dockerfile").read_text(encoding="utf-8")
    entrypoint = Path("docker/entrypoint.sh").read_text(encoding="utf-8")
    assert "/usr/local/bin/job-hunter-entrypoint" in dockerfile
    assert 'ENTRYPOINT ["job-hunter-entrypoint"]' in dockerfile
    assert "exec job-hunter" in entrypoint


def test_scheduler_is_available_in_the_base_runtime_install() -> None:
    """The application composition root can import its core scheduler dependency."""

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    assert any(dependency.startswith("APScheduler") for dependency in dependencies)


def test_compose_keeps_the_default_application_port_local() -> None:
    """A development Compose launch cannot accidentally expose unauthenticated data."""

    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8000:8000"' in compose


def test_base_layout_has_a_single_skip_target_and_no_nested_login_main() -> None:
    """Keyboard users can bypass navigation and login does not duplicate the main landmark."""

    base = Path("app/templates/base.html").read_text(encoding="utf-8")
    login = Path("app/templates/login.html").read_text(encoding="utf-8")
    assert 'href="#main-content"' in base
    assert 'id="main-content"' in base
    assert "<main" not in login
