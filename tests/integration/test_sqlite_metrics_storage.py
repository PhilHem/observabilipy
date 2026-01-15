"""Tests for SQLite metrics storage adapter."""

import pytest

from observabilipy.adapters.storage import SQLiteMetricsStorage
from observabilipy.core.models import MetricSample
from observabilipy.core.ports import MetricsStoragePort

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsMetricsStoragePort")
class TestSQLiteMetricsStorage:
    """Tests for SQLiteMetricsStorage adapter."""

    @pytest.mark.storage
    def test_implements_metrics_storage_port(self) -> None:
        """SQLiteMetricsStorage must satisfy MetricsStoragePort protocol."""
        storage = SQLiteMetricsStorage(":memory:")
        assert isinstance(storage, MetricsStoragePort)

    @pytest.mark.storage
    async def test_memory_database_write_and_scrape(
        self, memory_metrics_storage: SQLiteMetricsStorage
    ) -> None:
        """In-memory database should persist data within same instance."""
        sample = MetricSample(
            name="test_metric", timestamp=1000.0, value=42.0, labels={}
        )
        await memory_metrics_storage.write(sample)
        result = [s async for s in memory_metrics_storage.read()]
        assert len(result) == 1
        assert result[0].value == 42.0

    @pytest.mark.storage
    async def test_memory_database_multiple_operations(
        self, memory_metrics_storage: SQLiteMetricsStorage
    ) -> None:
        """Multiple writes and scrapes should work on in-memory database."""
        for i in range(3):
            sample = MetricSample(
                name=f"metric_{i}", timestamp=1000.0 + i, value=float(i), labels={}
            )
            await memory_metrics_storage.write(sample)
        assert await memory_metrics_storage.count() == 3

    @pytest.mark.storage
    async def test_memory_database_close(
        self, memory_metrics_storage: SQLiteMetricsStorage
    ) -> None:
        """Storage should have a close method for cleanup."""
        await memory_metrics_storage.write(
            MetricSample(name="metric", timestamp=1000.0, value=1.0, labels={})
        )
        await memory_metrics_storage.close()
        # After close, storage can be reinitialized
        await memory_metrics_storage.write(
            MetricSample(name="metric", timestamp=2000.0, value=2.0, labels={})
        )
        result = [s async for s in memory_metrics_storage.read()]
        assert len(result) == 1  # Only new entry, old DB was closed

    @pytest.mark.storage
    async def test_write_and_scrape_single_sample(self, metrics_db_path: str) -> None:
        """Can write a metric sample and scrape it back."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        sample = MetricSample(name="requests_total", timestamp=1000.0, value=42.0)

        await storage.write(sample)
        result = [s async for s in storage.read()]

        assert result == [sample]

    @pytest.mark.storage
    async def test_scrape_returns_empty_when_no_samples(
        self, metrics_db_path: str
    ) -> None:
        """Scrape returns empty iterable when storage is empty."""
        storage = SQLiteMetricsStorage(metrics_db_path)

        result = [s async for s in storage.read()]

        assert result == []

    @pytest.mark.storage
    async def test_write_and_scrape_sample_with_labels(
        self, metrics_db_path: str
    ) -> None:
        """Labels are correctly serialized and deserialized."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        sample = MetricSample(
            name="http_requests",
            timestamp=1000.0,
            value=10.0,
            labels={"method": "GET", "status": "200"},
        )

        await storage.write(sample)
        result = [s async for s in storage.read()]

        assert result[0].labels == {"method": "GET", "status": "200"}

    @pytest.mark.storage
    async def test_write_multiple_samples(self, metrics_db_path: str) -> None:
        """Can write multiple samples and scrape them all back."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        samples = [
            MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            for i in range(5)
        ]

        for sample in samples:
            await storage.write(sample)
        result = [s async for s in storage.read()]

        assert result == samples

    @pytest.mark.storage
    async def test_samples_with_different_labels_are_distinct(
        self, metrics_db_path: str
    ) -> None:
        """Samples with same name but different labels are stored separately."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        sample_a = MetricSample(
            name="http_requests",
            timestamp=1000.0,
            value=10.0,
            labels={"method": "GET"},
        )
        sample_b = MetricSample(
            name="http_requests",
            timestamp=1001.0,
            value=5.0,
            labels={"method": "POST"},
        )

        await storage.write(sample_a)
        await storage.write(sample_b)
        result = [s async for s in storage.read()]

        assert len(result) == 2
        assert sample_a in result
        assert sample_b in result

    @pytest.mark.storage
    async def test_count_returns_zero_when_empty(self, metrics_db_path: str) -> None:
        """Count returns 0 for empty storage."""
        storage = SQLiteMetricsStorage(metrics_db_path)

        count = await storage.count()

        assert count == 0

    @pytest.mark.storage
    async def test_count_returns_correct_count_after_writes(
        self, metrics_db_path: str
    ) -> None:
        """Count returns correct number of samples after writes."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        for i in range(5):
            await storage.write(
                MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            )

        count = await storage.count()

        assert count == 5

    @pytest.mark.storage
    async def test_delete_before_removes_old_samples(
        self, metrics_db_path: str
    ) -> None:
        """delete_before removes samples with timestamp < given value."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        old_sample = MetricSample(name="metric", timestamp=1000.0, value=1.0)
        new_sample = MetricSample(name="metric", timestamp=2000.0, value=2.0)
        await storage.write(old_sample)
        await storage.write(new_sample)

        await storage.delete_before(1500.0)

        result = [s async for s in storage.read()]
        assert result == [new_sample]

    @pytest.mark.storage
    async def test_delete_before_keeps_samples_at_or_after_timestamp(
        self, metrics_db_path: str
    ) -> None:
        """delete_before keeps samples with timestamp >= given value."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        sample_at = MetricSample(name="metric", timestamp=1500.0, value=1.0)
        sample_after = MetricSample(name="metric", timestamp=2000.0, value=2.0)
        await storage.write(sample_at)
        await storage.write(sample_after)

        await storage.delete_before(1500.0)

        result = [s async for s in storage.read()]
        assert sample_at in result
        assert sample_after in result

    @pytest.mark.storage
    async def test_delete_before_returns_deleted_count(
        self, metrics_db_path: str
    ) -> None:
        """delete_before returns the number of samples deleted."""
        storage = SQLiteMetricsStorage(metrics_db_path)
        for i in range(5):
            await storage.write(
                MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            )

        deleted = await storage.delete_before(1003.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_before_empty_storage(self, metrics_db_path: str) -> None:
        """delete_before on empty storage returns 0."""
        storage = SQLiteMetricsStorage(metrics_db_path)

        deleted = await storage.delete_before(1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_read_since_filters_by_timestamp(
        self, memory_metrics_storage: SQLiteMetricsStorage
    ) -> None:
        """read(since) only returns samples with timestamp > since."""
        await memory_metrics_storage.write(
            MetricSample(name="m", timestamp=100.0, value=1.0)
        )
        await memory_metrics_storage.write(
            MetricSample(name="m", timestamp=200.0, value=2.0)
        )
        await memory_metrics_storage.write(
            MetricSample(name="m", timestamp=300.0, value=3.0)
        )

        results = [s async for s in memory_metrics_storage.read(since=150.0)]

        assert len(results) == 2
        assert results[0].timestamp == 200.0
        assert results[1].timestamp == 300.0

    @pytest.mark.storage
    async def test_read_since_returns_ascending_order(
        self, memory_metrics_storage: SQLiteMetricsStorage
    ) -> None:
        """read() returns samples ordered by timestamp ascending."""
        await memory_metrics_storage.write(
            MetricSample(name="m", timestamp=300.0, value=3.0)
        )
        await memory_metrics_storage.write(
            MetricSample(name="m", timestamp=100.0, value=1.0)
        )

        results = [s async for s in memory_metrics_storage.read()]

        assert results[0].timestamp == 100.0
        assert results[1].timestamp == 300.0
