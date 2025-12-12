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

    @pytest.mark.storage
    async def test_delete_by_level_before_removes_matching_entries(self) -> None:
        """delete_by_level_before removes entries matching level and timestamp."""
        storage = InMemoryLogStorage()
        await storage.write(
            LogEntry(timestamp=100.0, level="ERROR", message="old error")
        )
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="old info"))
        await storage.write(
            LogEntry(timestamp=200.0, level="ERROR", message="new error")
        )

        deleted = await storage.delete_by_level_before("ERROR", 150.0)

        assert deleted == 1
        entries = [e async for e in storage.read()]
        assert len(entries) == 2
        assert all(e.message != "old error" for e in entries)

    @pytest.mark.storage
    async def test_delete_by_level_before_preserves_other_levels(self) -> None:
        """delete_by_level_before does not affect other log levels."""
        storage = InMemoryLogStorage()
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error"))
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        await storage.delete_by_level_before("ERROR", 150.0)

        entries = [e async for e in storage.read()]
        assert len(entries) == 1
        assert entries[0].level == "INFO"

    @pytest.mark.storage
    async def test_delete_by_level_before_returns_deleted_count(self) -> None:
        """delete_by_level_before returns number of entries deleted."""
        storage = InMemoryLogStorage()
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=100.0 + i, level="DEBUG", message=f"msg {i}")
            )

        deleted = await storage.delete_by_level_before("DEBUG", 103.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_by_level_before_empty_storage(self) -> None:
        """delete_by_level_before on empty storage returns 0."""
        storage = InMemoryLogStorage()

        deleted = await storage.delete_by_level_before("ERROR", 1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_count_by_level_returns_count_for_specific_level(self) -> None:
        """count_by_level returns count only for specified level."""
        storage = InMemoryLogStorage()
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error 1"))
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error 2"))
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await storage.count_by_level("ERROR")

        assert count == 2

    @pytest.mark.storage
    async def test_count_by_level_returns_zero_for_absent_level(self) -> None:
        """count_by_level returns 0 when no entries match level."""
        storage = InMemoryLogStorage()
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await storage.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.storage
    async def test_count_by_level_empty_storage(self) -> None:
        """count_by_level on empty storage returns 0."""
        storage = InMemoryLogStorage()

        count = await storage.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.storage
    async def test_read_filters_by_level(self) -> None:
        """Read with level parameter returns only matching entries."""
        storage = InMemoryLogStorage()
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")
        debug_entry = LogEntry(timestamp=1002.0, level="DEBUG", message="debug msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        await storage.write(debug_entry)
        result = [e async for e in storage.read(level="ERROR")]

        assert result == [error_entry]

    @pytest.mark.storage
    async def test_read_level_none_returns_all_entries(self) -> None:
        """Read with level=None returns all entries (backwards compatible)."""
        storage = InMemoryLogStorage()
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        result = [e async for e in storage.read(level=None)]

        assert result == [error_entry, info_entry]

    @pytest.mark.storage
    async def test_read_level_filter_is_case_insensitive(self) -> None:
        """Read level filter matches regardless of case."""
        storage = InMemoryLogStorage()
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        result = [e async for e in storage.read(level="error")]

        assert result == [error_entry]

    @pytest.mark.storage
    async def test_read_combines_since_and_level_filters(self) -> None:
        """Read combines both since and level filters."""
        storage = InMemoryLogStorage()
        old_error = LogEntry(timestamp=1000.0, level="ERROR", message="old error")
        new_error = LogEntry(timestamp=2000.0, level="ERROR", message="new error")
        new_info = LogEntry(timestamp=2001.0, level="INFO", message="new info")

        await storage.write(old_error)
        await storage.write(new_error)
        await storage.write(new_info)
        result = [e async for e in storage.read(since=1500.0, level="ERROR")]

        assert result == [new_error]

    @pytest.mark.storage
    async def test_read_level_returns_empty_for_nonexistent_level(self) -> None:
        """Read with non-existent level returns empty result."""
        storage = InMemoryLogStorage()
        info_entry = LogEntry(timestamp=1000.0, level="INFO", message="info msg")

        await storage.write(info_entry)
        result = [e async for e in storage.read(level="FATAL")]

        assert result == []


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
        result = [s async for s in storage.read()]

        assert result == [sample]

    @pytest.mark.storage
    async def test_scrape_returns_empty_when_no_samples(self) -> None:
        """Scrape returns empty iterable when storage is empty."""
        storage = InMemoryMetricsStorage()

        result = [s async for s in storage.read()]

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
        result = [s async for s in storage.read()]

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
        result = [s async for s in storage.read()]

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

        result = [s async for s in storage.read()]
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

        result = [s async for s in storage.read()]
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

    @pytest.mark.storage
    async def test_read_since_filters_by_timestamp(self) -> None:
        """read(since) only returns samples with timestamp > since."""
        storage = InMemoryMetricsStorage()
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))
        await storage.write(MetricSample(name="m", timestamp=200.0, value=2.0))
        await storage.write(MetricSample(name="m", timestamp=300.0, value=3.0))

        results = [s async for s in storage.read(since=150.0)]

        assert len(results) == 2
        assert results[0].timestamp == 200.0
        assert results[1].timestamp == 300.0

    @pytest.mark.storage
    async def test_read_since_zero_returns_all(self) -> None:
        """read() with default since=0 returns all samples."""
        storage = InMemoryMetricsStorage()
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))
        await storage.write(MetricSample(name="m", timestamp=200.0, value=2.0))

        results = [s async for s in storage.read()]

        assert len(results) == 2

    @pytest.mark.storage
    async def test_read_since_returns_ascending_order(self) -> None:
        """read() returns samples ordered by timestamp ascending."""
        storage = InMemoryMetricsStorage()
        await storage.write(MetricSample(name="m", timestamp=300.0, value=3.0))
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))

        results = [s async for s in storage.read()]

        assert results[0].timestamp == 100.0
        assert results[1].timestamp == 300.0
