"""Tests for ring buffer metrics storage adapter."""

import pytest

from observabilipy.adapters.storage.ring_buffer import RingBufferMetricsStorage
from observabilipy.core.exceptions import ConfigurationError
from observabilipy.core.models import MetricSample
from observabilipy.core.ports import MetricsStoragePort

# Unit tests - in-memory only, no I/O
pytestmark = pytest.mark.tier(1)


@pytest.mark.tra("Adapter.RingBufferStorage.ImplementsMetricsStoragePort")
class TestRingBufferMetricsStorage:
    """Tests for RingBufferMetricsStorage adapter."""

    @pytest.mark.storage
    def test_rejects_zero_max_size(self) -> None:
        """max_size=0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            RingBufferMetricsStorage(max_size=0)
        assert "max_size" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    @pytest.mark.storage
    def test_rejects_negative_max_size(self) -> None:
        """Negative max_size raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            RingBufferMetricsStorage(max_size=-1)

    @pytest.mark.storage
    def test_implements_metrics_storage_port(self) -> None:
        """RingBufferMetricsStorage must satisfy MetricsStoragePort protocol."""
        storage = RingBufferMetricsStorage(max_size=100)
        assert isinstance(storage, MetricsStoragePort)

    @pytest.mark.storage
    async def test_write_and_scrape_single_sample(self) -> None:
        """Can write a metric sample and scrape it back."""
        storage = RingBufferMetricsStorage(max_size=100)
        sample = MetricSample(name="requests_total", timestamp=1000.0, value=42.0)

        await storage.write(sample)
        result = [s async for s in storage.read()]

        assert result == [sample]

    @pytest.mark.storage
    async def test_scrape_returns_empty_when_no_samples(self) -> None:
        """Scrape returns empty iterable when storage is empty."""
        storage = RingBufferMetricsStorage(max_size=100)

        result = [s async for s in storage.read()]

        assert result == []

    @pytest.mark.storage
    async def test_write_multiple_samples(self) -> None:
        """Can write multiple samples and scrape them all back."""
        storage = RingBufferMetricsStorage(max_size=100)
        samples = [
            MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            for i in range(5)
        ]

        for sample in samples:
            await storage.write(sample)
        result = [s async for s in storage.read()]

        assert result == samples

    @pytest.mark.storage
    async def test_samples_with_different_labels_are_distinct(self) -> None:
        """Samples with same name but different labels are stored separately."""
        storage = RingBufferMetricsStorage(max_size=100)
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
    async def test_evicts_oldest_samples_when_full(self) -> None:
        """Oldest samples are evicted when buffer exceeds max_size."""
        storage = RingBufferMetricsStorage(max_size=3)
        samples = [
            MetricSample(name=f"m_{i}", timestamp=float(i), value=float(i))
            for i in range(5)  # Write 5 samples to buffer of size 3
        ]

        for sample in samples:
            await storage.write(sample)
        result = [s async for s in storage.read()]

        # Only last 3 should remain
        assert result == samples[2:]

    @pytest.mark.storage
    async def test_count_returns_zero_when_empty(self) -> None:
        """Count returns 0 for empty storage."""
        storage = RingBufferMetricsStorage(max_size=100)

        count = await storage.count()

        assert count == 0

    @pytest.mark.storage
    async def test_count_returns_correct_count_after_writes(self) -> None:
        """Count returns correct number of samples after writes."""
        storage = RingBufferMetricsStorage(max_size=100)
        for i in range(5):
            await storage.write(
                MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            )

        count = await storage.count()

        assert count == 5

    @pytest.mark.storage
    async def test_delete_before_removes_old_samples(self) -> None:
        """delete_before removes samples with timestamp < given value."""
        storage = RingBufferMetricsStorage(max_size=100)
        old_sample = MetricSample(name="metric", timestamp=1000.0, value=1.0)
        new_sample = MetricSample(name="metric", timestamp=2000.0, value=2.0)
        await storage.write(old_sample)
        await storage.write(new_sample)

        await storage.delete_before(1500.0)

        result = [s async for s in storage.read()]
        assert result == [new_sample]

    @pytest.mark.storage
    async def test_delete_before_keeps_samples_at_or_after_timestamp(self) -> None:
        """delete_before keeps samples with timestamp >= given value."""
        storage = RingBufferMetricsStorage(max_size=100)
        sample_at = MetricSample(name="metric", timestamp=1500.0, value=1.0)
        sample_after = MetricSample(name="metric", timestamp=2000.0, value=2.0)
        await storage.write(sample_at)
        await storage.write(sample_after)

        await storage.delete_before(1500.0)

        result = [s async for s in storage.read()]
        assert sample_at in result
        assert sample_after in result

    @pytest.mark.storage
    async def test_delete_before_returns_deleted_count(self) -> None:
        """delete_before returns the number of samples deleted."""
        storage = RingBufferMetricsStorage(max_size=100)
        for i in range(5):
            await storage.write(
                MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            )

        deleted = await storage.delete_before(1003.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_before_empty_storage(self) -> None:
        """delete_before on empty storage returns 0."""
        storage = RingBufferMetricsStorage(max_size=100)

        deleted = await storage.delete_before(1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_read_since_filters_by_timestamp(self) -> None:
        """read(since) only returns samples with timestamp > since."""
        storage = RingBufferMetricsStorage(max_size=10)
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))
        await storage.write(MetricSample(name="m", timestamp=200.0, value=2.0))

        results = [s async for s in storage.read(since=150.0)]

        assert len(results) == 1
        assert results[0].timestamp == 200.0

    @pytest.mark.storage
    async def test_read_since_returns_ascending_order(self) -> None:
        """read() returns samples ordered by timestamp ascending."""
        storage = RingBufferMetricsStorage(max_size=10)
        await storage.write(MetricSample(name="m", timestamp=300.0, value=3.0))
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))

        results = [s async for s in storage.read()]

        assert results[0].timestamp == 100.0
        assert results[1].timestamp == 300.0


@pytest.mark.tra("Adapter.RingBufferStorage.ImplementsMetricsStoragePort")
class TestRingBufferMetricsStorageSync:
    """Tests for synchronous methods on RingBufferMetricsStorage."""

    @pytest.mark.storage
    def test_write_sync_writes_single_sample(self) -> None:
        """write_sync() appends a single sample synchronously."""
        storage = RingBufferMetricsStorage(max_size=100)
        sample = MetricSample(name="test_metric", timestamp=1000.0, value=42.0)

        storage.write_sync(sample)

        assert len(storage._buffer) == 1
        assert storage._buffer[0] == sample

    @pytest.mark.storage
    def test_write_sync_respects_max_size(self) -> None:
        """write_sync() evicts oldest sample when buffer is full."""
        storage = RingBufferMetricsStorage(max_size=2)
        samples = [
            MetricSample(name=f"m_{i}", timestamp=float(i), value=float(i))
            for i in range(3)
        ]

        for sample in samples:
            storage.write_sync(sample)

        assert len(storage._buffer) == 2
        assert list(storage._buffer) == samples[1:]

    @pytest.mark.storage
    async def test_clear_removes_all_samples(self) -> None:
        """clear() removes all samples from storage."""
        storage = RingBufferMetricsStorage(max_size=100)
        await storage.write(MetricSample(name="m1", timestamp=1000.0, value=1.0))
        await storage.write(MetricSample(name="m2", timestamp=1001.0, value=2.0))

        await storage.clear()

        assert await storage.count() == 0

    @pytest.mark.storage
    def test_clear_sync_removes_all_samples(self) -> None:
        """clear_sync() removes all samples synchronously."""
        storage = RingBufferMetricsStorage(max_size=100)
        storage.write_sync(MetricSample(name="m1", timestamp=1000.0, value=1.0))
        storage.write_sync(MetricSample(name="m2", timestamp=1001.0, value=2.0))

        storage.clear_sync()

        assert len(storage._buffer) == 0
