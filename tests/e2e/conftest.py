"""Shared fixtures for E2E tests."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

# Guard framework imports - these conftest files are parsed even when running
# non-e2e tests, so we need to handle missing optional dependencies gracefully.
try:
    import httpx
    from fastapi import FastAPI

    from observabilipy.adapters.frameworks.fastapi import create_observability_router

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.adapters.storage.sqlite import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.core.models import RetentionPolicy


@pytest.fixture
def log_storage() -> InMemoryLogStorage:
    """Fresh in-memory log storage."""
    return InMemoryLogStorage()


@pytest.fixture
def metrics_storage() -> InMemoryMetricsStorage:
    """Fresh in-memory metrics storage."""
    return InMemoryMetricsStorage()


@pytest.fixture
def sqlite_log_db_path(tmp_path: Path) -> str:
    """Temporary path for SQLite log database."""
    return str(tmp_path / "logs.db")


@pytest.fixture
def sqlite_metrics_db_path(tmp_path: Path) -> str:
    """Temporary path for SQLite metrics database."""
    return str(tmp_path / "metrics.db")


@pytest.fixture
def sqlite_log_storage(sqlite_log_db_path: str) -> SQLiteLogStorage:
    """SQLite log storage with temp database."""
    return SQLiteLogStorage(sqlite_log_db_path)


@pytest.fixture
def sqlite_metrics_storage(sqlite_metrics_db_path: str) -> SQLiteMetricsStorage:
    """SQLite metrics storage with temp database."""
    return SQLiteMetricsStorage(sqlite_metrics_db_path)


# FastAPI-dependent fixtures - only defined when fastapi is available
if HAS_FASTAPI:

    @pytest.fixture
    def asgi_app(
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
    ) -> "FastAPI":
        """Create a FastAPI app with observability endpoints."""
        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        return app

    @pytest.fixture
    async def client(asgi_app: "FastAPI") -> AsyncGenerator[httpx.AsyncClient]:
        """HTTP client for making requests to the ASGI app."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=asgi_app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.fixture
    def sqlite_asgi_app(
        sqlite_log_storage: SQLiteLogStorage,
        sqlite_metrics_storage: SQLiteMetricsStorage,
    ) -> "FastAPI":
        """Create a FastAPI app with SQLite-backed observability endpoints."""
        app = FastAPI()
        app.include_router(
            create_observability_router(sqlite_log_storage, sqlite_metrics_storage)
        )
        return app

    @pytest.fixture
    async def sqlite_client(
        sqlite_asgi_app: "FastAPI",
    ) -> AsyncGenerator[httpx.AsyncClient]:
        """HTTP client for SQLite-backed app."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=sqlite_asgi_app),
            base_url="http://test",
        ) as client:
            yield client


@pytest.fixture
def retention_policy_short() -> RetentionPolicy:
    """Retention policy for testing (very short for fast tests)."""
    return RetentionPolicy(max_age_seconds=0.1)


@pytest.fixture
def retention_policy_count() -> RetentionPolicy:
    """Retention policy based on count."""
    return RetentionPolicy(max_count=3)
