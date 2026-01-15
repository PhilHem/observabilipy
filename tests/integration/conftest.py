"""Shared fixtures for integration tests."""

from collections.abc import AsyncGenerator

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage, SQLiteMetricsStorage


@pytest.fixture
async def memory_log_storage() -> AsyncGenerator[SQLiteLogStorage]:
    """In-memory log storage with proper cleanup."""
    storage = SQLiteLogStorage(":memory:")
    yield storage
    await storage.close()


@pytest.fixture
async def memory_metrics_storage() -> AsyncGenerator[SQLiteMetricsStorage]:
    """In-memory metrics storage with proper cleanup."""
    storage = SQLiteMetricsStorage(":memory:")
    yield storage
    await storage.close()
