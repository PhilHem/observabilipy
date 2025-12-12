"""Tests for SQLite storage adapters."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from observabilipy.adapters.storage.sqlite import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.core.models import LogEntry, MetricSample
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


@pytest.fixture
def log_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for log storage tests."""
    return str(tmp_path / "logs.db")


@pytest.fixture
def metrics_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for metrics storage tests."""
    return str(tmp_path / "metrics.db")


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


class TestSQLiteLogStorage:
    """Tests for SQLiteLogStorage adapter."""

    @pytest.mark.storage
    def test_implements_log_storage_port(self) -> None:
        """SQLiteLogStorage must satisfy LogStoragePort protocol."""
        storage = SQLiteLogStorage(":memory:")
        assert isinstance(storage, LogStoragePort)

    @pytest.mark.storage
    async def test_memory_database_write_and_read(
        self, memory_log_storage: SQLiteLogStorage
    ) -> None:
        """In-memory database should persist data within same instance."""
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test", attributes={})
        await memory_log_storage.write(entry)
        result = [e async for e in memory_log_storage.read()]
        assert len(result) == 1
        assert result[0].message == "test"

    @pytest.mark.storage
    async def test_memory_database_multiple_operations(
        self, memory_log_storage: SQLiteLogStorage
    ) -> None:
        """Multiple writes and reads should work on in-memory database."""
        for i in range(3):
            entry = LogEntry(
                timestamp=1000.0 + i, level="INFO", message=f"msg{i}", attributes={}
            )
            await memory_log_storage.write(entry)
        assert await memory_log_storage.count() == 3

    @pytest.mark.storage
    async def test_memory_database_close(
        self, memory_log_storage: SQLiteLogStorage
    ) -> None:
        """Storage should have a close method for cleanup."""
        await memory_log_storage.write(
            LogEntry(timestamp=1000.0, level="INFO", message="test", attributes={})
        )
        await memory_log_storage.close()
        # After close, storage can be reinitialized
        await memory_log_storage.write(
            LogEntry(timestamp=2000.0, level="INFO", message="test2", attributes={})
        )
        result = [e async for e in memory_log_storage.read()]
        assert len(result) == 1  # Only new entry, old DB was closed

    @pytest.mark.storage
    async def test_write_and_read_single_entry(self, log_db_path: str) -> None:
        """Can write a log entry and read it back."""
        storage = SQLiteLogStorage(log_db_path)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test message")

        await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result == [entry]

    @pytest.mark.storage
    async def test_read_returns_empty_when_no_entries(self, log_db_path: str) -> None:
        """Read returns empty iterable when storage is empty."""
        storage = SQLiteLogStorage(log_db_path)

        result = [e async for e in storage.read()]

        assert result == []

    @pytest.mark.storage
    async def test_read_filters_by_since_timestamp(self, log_db_path: str) -> None:
        """Read only returns entries with timestamp > since."""
        storage = SQLiteLogStorage(log_db_path)
        old_entry = LogEntry(timestamp=1000.0, level="INFO", message="old")
        new_entry = LogEntry(timestamp=2000.0, level="INFO", message="new")

        await storage.write(old_entry)
        await storage.write(new_entry)
        result = [e async for e in storage.read(since=1000.0)]

        assert result == [new_entry]

    @pytest.mark.storage
    async def test_read_returns_entries_ordered_by_timestamp(
        self, log_db_path: str
    ) -> None:
        """Read returns entries ordered by timestamp ascending."""
        storage = SQLiteLogStorage(log_db_path)
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
    async def test_write_and_read_entry_with_attributes(self, log_db_path: str) -> None:
        """Attributes are correctly serialized and deserialized."""
        storage = SQLiteLogStorage(log_db_path)
        entry = LogEntry(
            timestamp=1000.0,
            level="INFO",
            message="test",
            attributes={"user_id": 123, "flag": True, "ratio": 0.5},
        )

        await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result[0].attributes == {"user_id": 123, "flag": True, "ratio": 0.5}

    @pytest.mark.storage
    async def test_write_multiple_entries(self, log_db_path: str) -> None:
        """Can write multiple entries and read them all back."""
        storage = SQLiteLogStorage(log_db_path)
        entries = [
            LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            for i in range(5)
        ]

        for entry in entries:
            await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result == entries

    @pytest.mark.storage
    async def test_count_returns_zero_when_empty(self, log_db_path: str) -> None:
        """Count returns 0 for empty storage."""
        storage = SQLiteLogStorage(log_db_path)

        count = await storage.count()

        assert count == 0

    @pytest.mark.storage
    async def test_count_returns_correct_count_after_writes(
        self, log_db_path: str
    ) -> None:
        """Count returns correct number of entries after writes."""
        storage = SQLiteLogStorage(log_db_path)
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            )

        count = await storage.count()

        assert count == 5

    @pytest.mark.storage
    async def test_delete_before_removes_old_entries(self, log_db_path: str) -> None:
        """delete_before removes entries with timestamp < given value."""
        storage = SQLiteLogStorage(log_db_path)
        old_entry = LogEntry(timestamp=1000.0, level="INFO", message="old")
        new_entry = LogEntry(timestamp=2000.0, level="INFO", message="new")
        await storage.write(old_entry)
        await storage.write(new_entry)

        await storage.delete_before(1500.0)

        result = [e async for e in storage.read()]
        assert result == [new_entry]

    @pytest.mark.storage
    async def test_delete_before_keeps_entries_at_or_after_timestamp(
        self, log_db_path: str
    ) -> None:
        """delete_before keeps entries with timestamp >= given value."""
        storage = SQLiteLogStorage(log_db_path)
        entry_at = LogEntry(timestamp=1500.0, level="INFO", message="at boundary")
        entry_after = LogEntry(timestamp=2000.0, level="INFO", message="after")
        await storage.write(entry_at)
        await storage.write(entry_after)

        await storage.delete_before(1500.0)

        result = [e async for e in storage.read()]
        assert entry_at in result
        assert entry_after in result

    @pytest.mark.storage
    async def test_delete_before_returns_deleted_count(self, log_db_path: str) -> None:
        """delete_before returns the number of entries deleted."""
        storage = SQLiteLogStorage(log_db_path)
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            )

        deleted = await storage.delete_before(1003.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_before_empty_storage(self, log_db_path: str) -> None:
        """delete_before on empty storage returns 0."""
        storage = SQLiteLogStorage(log_db_path)

        deleted = await storage.delete_before(1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_delete_by_level_before_removes_matching_entries(
        self, log_db_path: str
    ) -> None:
        """delete_by_level_before removes entries matching level and timestamp."""
        storage = SQLiteLogStorage(log_db_path)
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
    async def test_delete_by_level_before_preserves_other_levels(
        self, log_db_path: str
    ) -> None:
        """delete_by_level_before does not affect other log levels."""
        storage = SQLiteLogStorage(log_db_path)
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error"))
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        await storage.delete_by_level_before("ERROR", 150.0)

        entries = [e async for e in storage.read()]
        assert len(entries) == 1
        assert entries[0].level == "INFO"

    @pytest.mark.storage
    async def test_delete_by_level_before_returns_deleted_count(
        self, log_db_path: str
    ) -> None:
        """delete_by_level_before returns number of entries deleted."""
        storage = SQLiteLogStorage(log_db_path)
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=100.0 + i, level="DEBUG", message=f"msg {i}")
            )

        deleted = await storage.delete_by_level_before("DEBUG", 103.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_by_level_before_empty_storage(self, log_db_path: str) -> None:
        """delete_by_level_before on empty storage returns 0."""
        storage = SQLiteLogStorage(log_db_path)

        deleted = await storage.delete_by_level_before("ERROR", 1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_count_by_level_returns_count_for_specific_level(
        self, log_db_path: str
    ) -> None:
        """count_by_level returns count only for specified level."""
        storage = SQLiteLogStorage(log_db_path)
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error 1"))
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error 2"))
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await storage.count_by_level("ERROR")

        assert count == 2

    @pytest.mark.storage
    async def test_count_by_level_returns_zero_for_absent_level(
        self, log_db_path: str
    ) -> None:
        """count_by_level returns 0 when no entries match level."""
        storage = SQLiteLogStorage(log_db_path)
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await storage.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.storage
    async def test_count_by_level_empty_storage(self, log_db_path: str) -> None:
        """count_by_level on empty storage returns 0."""
        storage = SQLiteLogStorage(log_db_path)

        count = await storage.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.storage
    async def test_read_filters_by_level(self, log_db_path: str) -> None:
        """Read with level parameter returns only matching entries."""
        storage = SQLiteLogStorage(log_db_path)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")
        debug_entry = LogEntry(timestamp=1002.0, level="DEBUG", message="debug msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        await storage.write(debug_entry)
        result = [e async for e in storage.read(level="ERROR")]

        assert result == [error_entry]

    @pytest.mark.storage
    async def test_read_level_none_returns_all_entries(self, log_db_path: str) -> None:
        """Read with level=None returns all entries (backwards compatible)."""
        storage = SQLiteLogStorage(log_db_path)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        result = [e async for e in storage.read(level=None)]

        assert result == [error_entry, info_entry]

    @pytest.mark.storage
    async def test_read_level_filter_is_case_insensitive(
        self, log_db_path: str
    ) -> None:
        """Read level filter matches regardless of case."""
        storage = SQLiteLogStorage(log_db_path)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        result = [e async for e in storage.read(level="error")]

        assert result == [error_entry]

    @pytest.mark.storage
    async def test_read_combines_since_and_level_filters(
        self, log_db_path: str
    ) -> None:
        """Read combines both since and level filters."""
        storage = SQLiteLogStorage(log_db_path)
        old_error = LogEntry(timestamp=1000.0, level="ERROR", message="old error")
        new_error = LogEntry(timestamp=2000.0, level="ERROR", message="new error")
        new_info = LogEntry(timestamp=2001.0, level="INFO", message="new info")

        await storage.write(old_error)
        await storage.write(new_error)
        await storage.write(new_info)
        result = [e async for e in storage.read(since=1500.0, level="ERROR")]

        assert result == [new_error]

    @pytest.mark.storage
    async def test_read_level_returns_empty_for_nonexistent_level(
        self, log_db_path: str
    ) -> None:
        """Read with non-existent level returns empty result."""
        storage = SQLiteLogStorage(log_db_path)
        info_entry = LogEntry(timestamp=1000.0, level="INFO", message="info msg")

        await storage.write(info_entry)
        result = [e async for e in storage.read(level="FATAL")]

        assert result == []


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


class TestSQLitePersistence:
    """Tests for data persistence across storage instances."""

    @pytest.mark.storage
    async def test_log_data_persists_across_instances(self, tmp_path: Path) -> None:
        """Log entries persist in file and are readable by new instances."""
        db_path = str(tmp_path / "persist_logs.db")

        # Write with first instance
        storage1 = SQLiteLogStorage(db_path)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="persisted")
        await storage1.write(entry)

        # Read with second instance
        storage2 = SQLiteLogStorage(db_path)
        result = [e async for e in storage2.read()]

        assert result == [entry]

    @pytest.mark.storage
    async def test_metrics_data_persists_across_instances(self, tmp_path: Path) -> None:
        """Metric samples persist in file and are readable by new instances."""
        db_path = str(tmp_path / "persist_metrics.db")

        # Write with first instance
        storage1 = SQLiteMetricsStorage(db_path)
        sample = MetricSample(name="requests_total", timestamp=1000.0, value=42.0)
        await storage1.write(sample)

        # Read with second instance
        storage2 = SQLiteMetricsStorage(db_path)
        result = [s async for s in storage2.read()]

        assert result == [sample]
