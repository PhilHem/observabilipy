"""Storage fixtures for E2E tests."""

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)


@pytest.fixture
def log_storage() -> InMemoryLogStorage:
    """Fresh in-memory log storage."""
    return InMemoryLogStorage()


@pytest.fixture
def metrics_storage() -> InMemoryMetricsStorage:
    """Fresh in-memory metrics storage."""
    return InMemoryMetricsStorage()


@pytest.fixture
def sqlite_log_storage(log_db_path: str) -> SQLiteLogStorage:
    """SQLite log storage with temp database."""
    return SQLiteLogStorage(log_db_path)


@pytest.fixture
def sqlite_metrics_storage(metrics_db_path: str) -> SQLiteMetricsStorage:
    """SQLite metrics storage with temp database."""
    return SQLiteMetricsStorage(metrics_db_path)
