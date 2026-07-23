"""Measure inexpensive local startup and endpoint latency for release evidence.

Run this on the target Raspberry Pi with a production-like configuration. The
script reports its platform and does not claim a target-device result elsewhere.
"""

from __future__ import annotations

import argparse
import platform
import time
import tracemalloc
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database.engine import create_database_engine
from app.main import create_app


def main() -> None:
    """Measure isolated startup and inexpensive request timings, then print evidence."""

    arguments = _arguments()
    settings = Settings.model_validate(
        {
            "app": {"environment": "testing"},
            "database": {"url": f"sqlite:///{arguments.database.resolve()}"},
            "logging": {"json_logs": False},
            "security": {"trusted_hosts": ["testserver"]},
        }
    )
    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    tracemalloc.start()
    started_at = time.perf_counter()
    with TestClient(create_app(settings)) as client:
        startup_ms = (time.perf_counter() - started_at) * 1_000
        health_ms = _request_ms(client, "/api/v1/health")
        dashboard_ms = _request_ms(client, "/dashboard")
        _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"platform={platform.platform()}")
    print(f"startup_ms={startup_ms:.2f}")
    print(f"health_ms={health_ms:.2f}")
    print(f"dashboard_ms={dashboard_ms:.2f}")
    print(f"python_peak_bytes={peak_bytes}")


def _arguments() -> argparse.Namespace:
    """Parse the isolated benchmark database location."""

    parser = argparse.ArgumentParser(description="Measure local Job-Hunter baseline performance")
    parser.add_argument("--database", type=Path, default=Path("data/benchmark.db"))
    return parser.parse_args()


def _request_ms(client: TestClient, path: str) -> float:
    """Measure one successful lightweight endpoint request."""

    started_at = time.perf_counter()
    response = client.get(path)
    response.raise_for_status()
    return (time.perf_counter() - started_at) * 1_000


if __name__ == "__main__":
    main()
