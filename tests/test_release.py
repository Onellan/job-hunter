"""Release-safety checks for the lightweight container and package defaults."""

from __future__ import annotations

import tomllib
from pathlib import Path

_JOBSPY_FORK_COMMIT = "7160d0faeda408d246e6948f2cc28ec253883375"
_JOBSPY_FORK_REQUIREMENT = (
    "python-jobspy @ https://github.com/Onellan/JobSpy/archive/" f"{_JOBSPY_FORK_COMMIT}.tar.gz"
)


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


def test_base_runtime_includes_all_discovered_provider_and_export_dependencies() -> None:
    """Normal and development installs include every built-in provider dependency."""

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    expected = {
        "beautifulsoup4>=4.12,<5",
        "lxml>=5,<7",
        "playwright>=1.50,<2",
        _JOBSPY_FORK_REQUIREMENT,
        "XlsxWriter>=3.2,<4",
    }

    assert expected.issubset(dependencies)


def test_jobspy_dependency_is_an_immutable_numpy_compatible_fork_source() -> None:
    """Every JobSpy install path resolves the reviewed source commit, not PyPI metadata."""

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependency_groups = (
        project["project"]["dependencies"],
        project["project"]["optional-dependencies"]["jobspy"],
        project["project"]["optional-dependencies"]["providers"],
    )

    assert all(_JOBSPY_FORK_REQUIREMENT in dependencies for dependencies in dependency_groups)
    assert all(
        not dependency.startswith("python-jobspy==")
        for dependencies in dependency_groups
        for dependency in dependencies
    )
    assert "git+" not in _JOBSPY_FORK_REQUIREMENT
    assert project["tool"]["hatch"]["metadata"]["allow-direct-references"] is True


def test_container_installs_chromium_during_the_root_build_layer() -> None:
    """The portable image bakes Playwright Chromium in before switching users."""

    dockerfile = Path("docker/Dockerfile").read_text(encoding="utf-8")
    entrypoint = Path("docker/entrypoint.sh").read_text(encoding="utf-8")

    assert "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" in dockerfile
    assert "python -m playwright install --with-deps chromium" in dockerfile
    assert dockerfile.index("python -m playwright install --with-deps chromium") < dockerfile.index(
        "USER jobhunter"
    )
    assert "linux/amd64" not in dockerfile
    assert "linux/arm64" not in dockerfile
    assert "playwright install" not in entrypoint


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
