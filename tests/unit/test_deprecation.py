"""Tests for deprecation warnings."""

import warnings
from collections.abc import AsyncGenerator

import pytest

from observabilipy.adapters.storage.in_memory import InMemoryMetricsStorage
from observabilipy.adapters.storage.ring_buffer import RingBufferMetricsStorage
from observabilipy.adapters.storage.sqlite import SQLiteMetricsStorage
from observabilipy.core.models import MetricSample


@pytest.fixture
async def memory_metrics_storage() -> AsyncGenerator[SQLiteMetricsStorage]:
    """Fixture for in-memory SQLite metrics storage."""
    storage = SQLiteMetricsStorage(":memory:")
    yield storage
    await storage.close()


@pytest.mark.core
async def test_in_memory_scrape_emits_deprecation_warning() -> None:
    """InMemoryMetricsStorage.scrape() should emit DeprecationWarning."""
    storage = InMemoryMetricsStorage()
    await storage.write(MetricSample(name="test", value=1.0, timestamp=1.0))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = [s async for s in storage.scrape()]

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "scrape() is deprecated" in str(w[0].message)
        assert "read()" in str(w[0].message)


@pytest.mark.core
async def test_ring_buffer_scrape_emits_deprecation_warning() -> None:
    """RingBufferMetricsStorage.scrape() should emit DeprecationWarning."""
    storage = RingBufferMetricsStorage(max_size=100)
    await storage.write(MetricSample(name="test", value=1.0, timestamp=1.0))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = [s async for s in storage.scrape()]

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "scrape() is deprecated" in str(w[0].message)
        assert "read()" in str(w[0].message)


@pytest.mark.storage
async def test_sqlite_scrape_emits_deprecation_warning(
    memory_metrics_storage: SQLiteMetricsStorage,
) -> None:
    """SQLiteMetricsStorage.scrape() should emit DeprecationWarning."""
    await memory_metrics_storage.write(
        MetricSample(name="test", value=1.0, timestamp=1.0)
    )

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = [s async for s in memory_metrics_storage.scrape()]

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "scrape() is deprecated" in str(w[0].message)
        assert "read()" in str(w[0].message)
