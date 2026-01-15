"""FastAPI app fixtures for E2E tests."""

from collections.abc import AsyncGenerator

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

if HAS_FASTAPI:
    from observabilipy.adapters.storage import SQLiteLogStorage, SQLiteMetricsStorage
    from observabilipy.adapters.storage.in_memory import (
        InMemoryLogStorage,
        InMemoryMetricsStorage,
    )

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
