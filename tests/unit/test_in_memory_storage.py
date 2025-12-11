"""Tests for in-memory storage adapters."""

import pytest

from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


class TestInMemoryLogStorage:
    """Tests for InMemoryLogStorage adapter."""

    @pytest.mark.storage
    def test_implements_log_storage_port(self) -> None:
        """InMemoryLogStorage must satisfy LogStoragePort protocol."""
        storage = InMemoryLogStorage()
        assert isinstance(storage, LogStoragePort)

    @pytest.mark.storage
    async def test_write_and_read_single_entry(self) -> None:
        """Can write a log entry and read it back."""
        storage = InMemoryLogStorage()
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test message")

        await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result == [entry]

    @pytest.mark.storage
    async def test_read_returns_empty_when_no_entries(self) -> None:
        """Read returns empty iterable when storage is empty."""
        storage = InMemoryLogStorage()

        result = [e async for e in storage.read()]

        assert result == []

    @pytest.mark.storage
    async def test_read_filters_by_since_timestamp(self) -> None:
        """Read only returns entries with timestamp > since."""
        storage = InMemoryLogStorage()
        old_entry = LogEntry(timestamp=1000.0, level="INFO", message="old")
        new_entry = LogEntry(timestamp=2000.0, level="INFO", message="new")

        await storage.write(old_entry)
        await storage.write(new_entry)
        result = [e async for e in storage.read(since=1000.0)]

        assert result == [new_entry]

    @pytest.mark.storage
    async def test_read_returns_entries_ordered_by_timestamp(self) -> None:
        """Read returns entries ordered by timestamp ascending."""
        storage = InMemoryLogStorage()
        entry_3 = LogEntry(timestamp=3000.0, level="INFO", message="third")
        entry_1 = LogEntry(timestamp=1000.0, level="INFO", message="first")
        entry_2 = LogEntry(timestamp=2000.0, level="INFO", message="second")

        # Write out of order
        await storage.write(entry_3)
        await storage.write(entry_1)
        await storage.write(entry_2)
        result = [e async for e in storage.read()]

        assert result == [entry_1, entry_2, entry_3]

    @pytest.mark.storage
    async def test_write_multiple_entries(self) -> None:
        """Can write multiple entries and read them all back."""
        storage = InMemoryLogStorage()
        entries = [
            LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            for i in range(5)
        ]

        for entry in entries:
            await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result == entries

    @pytest.mark.storage
    async def test_count_returns_zero_when_empty(self) -> None:
        """Count returns 0 for empty storage."""
        storage = InMemoryLogStorage()

        count = await storage.count()

        assert count == 0

    @pytest.mark.storage
    async def test_count_returns_correct_count_after_writes(self) -> None:
        """Count returns correct number of entries after writes."""
        storage = InMemoryLogStorage()
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            )

        count = await storage.count()

        assert count == 5

    @pytest.mark.storage
    async def test_delete_before_removes_old_entries(self) -> None:
        """delete_before removes entries with timestamp < given value."""
        storage = InMemoryLogStorage()
        old_entry = LogEntry(timestamp=1000.0, level="INFO", message="old")
        new_entry = LogEntry(timestamp=2000.0, level="INFO", message="new")
        await storage.write(old_entry)
        await storage.write(new_entry)

        await storage.delete_before(1500.0)

        result = [e async for e in storage.read()]
        assert result == [new_entry]

    @pytest.mark.storage
    async def test_delete_before_keeps_entries_at_or_after_timestamp(self) -> None:
        """delete_before keeps entries with timestamp >= given value."""
        storage = InMemoryLogStorage()
        entry_at = LogEntry(timestamp=1500.0, level="INFO", message="at boundary")
        entry_after = LogEntry(timestamp=2000.0, level="INFO", message="after")
        await storage.write(entry_at)
        await storage.write(entry_after)

        await storage.delete_before(1500.0)

        result = [e async for e in storage.read()]
        assert entry_at in result
        assert entry_after in result

    @pytest.mark.storage
    async def test_delete_before_returns_deleted_count(self) -> None:
        """delete_before returns the number of entries deleted."""
        storage = InMemoryLogStorage()
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            )

        deleted = await storage.delete_before(1003.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_before_empty_storage(self) -> None:
        """delete_before on empty storage returns 0."""
        storage = InMemoryLogStorage()

        deleted = await storage.delete_before(1000.0)

        assert deleted == 0


class TestInMemoryMetricsStorage:
    """Tests for InMemoryMetricsStorage adapter."""

    @pytest.mark.storage
    def test_implements_metrics_storage_port(self) -> None:
        """InMemoryMetricsStorage must satisfy MetricsStoragePort protocol."""
        storage = InMemoryMetricsStorage()
        assert isinstance(storage, MetricsStoragePort)

    @pytest.mark.storage
    async def test_write_and_scrape_single_sample(self) -> None:
        """Can write a metric sample and scrape it back."""
        storage = InMemoryMetricsStorage()
        sample = MetricSample(name="requests_total", timestamp=1000.0, value=42.0)

        await storage.write(sample)
        result = [s async for s in storage.scrape()]

        assert result == [sample]

    @pytest.mark.storage
    async def test_scrape_returns_empty_when_no_samples(self) -> None:
        """Scrape returns empty iterable when storage is empty."""
        storage = InMemoryMetricsStorage()

        result = [s async for s in storage.scrape()]

        assert result == []

    @pytest.mark.storage
    async def test_write_multiple_samples(self) -> None:
        """Can write multiple samples and scrape them all back."""
        storage = InMemoryMetricsStorage()
        samples = [
            MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            for i in range(5)
        ]

        for sample in samples:
            await storage.write(sample)
        result = [s async for s in storage.scrape()]

        assert result == samples

    @pytest.mark.storage
    async def test_samples_with_different_labels_are_distinct(self) -> None:
        """Samples with same name but different labels are stored separately."""
        storage = InMemoryMetricsStorage()
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
        result = [s async for s in storage.scrape()]

        assert len(result) == 2
        assert sample_a in result
        assert sample_b in result

    @pytest.mark.storage
    async def test_count_returns_zero_when_empty(self) -> None:
        """Count returns 0 for empty storage."""
        storage = InMemoryMetricsStorage()

        count = await storage.count()

        assert count == 0

    @pytest.mark.storage
    async def test_count_returns_correct_count_after_writes(self) -> None:
        """Count returns correct number of samples after writes."""
        storage = InMemoryMetricsStorage()
        for i in range(5):
            await storage.write(
                MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            )

        count = await storage.count()

        assert count == 5

    @pytest.mark.storage
    async def test_delete_before_removes_old_samples(self) -> None:
        """delete_before removes samples with timestamp < given value."""
        storage = InMemoryMetricsStorage()
        old_sample = MetricSample(name="metric", timestamp=1000.0, value=1.0)
        new_sample = MetricSample(name="metric", timestamp=2000.0, value=2.0)
        await storage.write(old_sample)
        await storage.write(new_sample)

        await storage.delete_before(1500.0)

        result = [s async for s in storage.scrape()]
        assert result == [new_sample]

    @pytest.mark.storage
    async def test_delete_before_keeps_samples_at_or_after_timestamp(self) -> None:
        """delete_before keeps samples with timestamp >= given value."""
        storage = InMemoryMetricsStorage()
        sample_at = MetricSample(name="metric", timestamp=1500.0, value=1.0)
        sample_after = MetricSample(name="metric", timestamp=2000.0, value=2.0)
        await storage.write(sample_at)
        await storage.write(sample_after)

        await storage.delete_before(1500.0)

        result = [s async for s in storage.scrape()]
        assert sample_at in result
        assert sample_after in result

    @pytest.mark.storage
    async def test_delete_before_returns_deleted_count(self) -> None:
        """delete_before returns the number of samples deleted."""
        storage = InMemoryMetricsStorage()
        for i in range(5):
            await storage.write(
                MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            )

        deleted = await storage.delete_before(1003.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_before_empty_storage(self) -> None:
        """delete_before on empty storage returns 0."""
        storage = InMemoryMetricsStorage()

        deleted = await storage.delete_before(1000.0)

        assert deleted == 0
