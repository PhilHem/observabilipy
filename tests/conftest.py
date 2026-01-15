"""Shared test fixtures for all test modules."""

from pathlib import Path

import pytest


@pytest.fixture
def log_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for log storage tests."""
    return str(tmp_path / "logs.db")


@pytest.fixture
def metrics_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for metrics storage tests."""
    return str(tmp_path / "metrics.db")


# Aliases for e2e tests that use sqlite_* prefix naming
@pytest.fixture
def sqlite_log_db_path(log_db_path: str) -> str:
    """Alias for log_db_path (used by e2e tests)."""
    return log_db_path


@pytest.fixture
def sqlite_metrics_db_path(metrics_db_path: str) -> str:
    """Alias for metrics_db_path (used by e2e tests)."""
    return metrics_db_path
