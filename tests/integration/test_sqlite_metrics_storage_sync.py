"""Tests for SQLite metrics storage adapter synchronous methods."""

import pytest

from observabilipy.adapters.storage import SQLiteMetricsStorage
from observabilipy.core.models import MetricSample

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsMetricsStoragePort")
class TestSQLiteMetricsStorageSync:
    """Tests for synchronous methods on SQLiteMetricsStorage."""

    @pytest.mark.storage
    def test_write_sync_writes_single_sample(self, metrics_db_path: str) -> None:
        """write_sync() inserts a single sample synchronously."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        sample = MetricSample(name="test_metric", timestamp=1000.0, value=42.0)

        storage.write_sync(sample)

        # Verify by reading back synchronously
        samples = storage.read_sync()
        assert samples == [sample]

    @pytest.mark.storage
    def test_write_sync_multiple_samples(self, metrics_db_path: str) -> None:
        """write_sync() can write multiple samples sequentially."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        samples = [
            MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            for i in range(3)
        ]

        for sample in samples:
            storage.write_sync(sample)

        result = storage.read_sync()
        assert result == samples

    @pytest.mark.storage
    async def test_clear_removes_all_samples(self, metrics_db_path: str) -> None:
        """clear() removes all samples from storage."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        await storage.write(MetricSample(name="m1", timestamp=1000.0, value=1.0))
        await storage.write(MetricSample(name="m2", timestamp=1001.0, value=2.0))

        await storage.clear()

        assert await storage.count() == 0

    @pytest.mark.storage
    def test_clear_sync_removes_all_samples(self, metrics_db_path: str) -> None:
        """clear_sync() removes all samples synchronously."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        storage.write_sync(MetricSample(name="m1", timestamp=1000.0, value=1.0))
        storage.write_sync(MetricSample(name="m2", timestamp=1001.0, value=2.0))

        storage.clear_sync()

        samples = storage.read_sync()
        assert samples == []

    @pytest.mark.storage
    async def test_sync_and_async_share_same_file_db(
        self, metrics_db_path: str
    ) -> None:
        """Sync and async methods share data for file-based databases."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        sample_sync = MetricSample(name="sync_metric", timestamp=1000.0, value=1.0)
        sample_async = MetricSample(name="async_metric", timestamp=1001.0, value=2.0)

        # Write sync
        storage.write_sync(sample_sync)

        # Write async
        await storage.write(sample_async)

        # Read sync - should see both
        samples = storage.read_sync()
        assert len(samples) == 2
        assert sample_sync in samples
        assert sample_async in samples
