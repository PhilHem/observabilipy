"""Tests for in-memory storage base class and protocol compliance."""

from dataclasses import dataclass

import pytest

from observabilipy.adapters.storage.in_memory import (
    InMemoryStorage,
    Timestamped,
)
from observabilipy.core.models import LogEntry, MetricSample

pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.tra("Adapter.InMemoryStorage.BaseClass"),
]


class TestTimestampedProtocol:
    """Tests for Timestamped protocol compliance."""

    @pytest.mark.storage
    def test_log_entry_satisfies_timestamped_protocol(self) -> None:
        """LogEntry must satisfy Timestamped protocol."""
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")
        assert isinstance(entry, Timestamped)

    @pytest.mark.storage
    def test_metric_sample_satisfies_timestamped_protocol(self) -> None:
        """MetricSample must satisfy Timestamped protocol."""
        sample = MetricSample(name="test", timestamp=1000.0, value=1.0)
        assert isinstance(sample, Timestamped)

    @pytest.mark.storage
    def test_arbitrary_class_with_timestamp_satisfies_protocol(self) -> None:
        """Any class with a timestamp property satisfies Timestamped."""

        @dataclass
        class CustomTimestamped:
            timestamp: float
            data: str

        obj = CustomTimestamped(timestamp=1000.0, data="test")
        assert isinstance(obj, Timestamped)


class TestInMemoryStorageBase:
    """Tests for InMemoryStorage base class common operations."""

    @pytest.mark.storage
    async def test_base_class_write_and_count(self) -> None:
        """Base class write and count work for any Timestamped type."""
        storage: InMemoryStorage[LogEntry] = InMemoryStorage()
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")

        await storage.write(entry)

        assert await storage.count() == 1

    @pytest.mark.storage
    async def test_base_class_clear(self) -> None:
        """Base class clear removes all items."""
        storage: InMemoryStorage[MetricSample] = InMemoryStorage()
        await storage.write(MetricSample(name="m", timestamp=1.0, value=1.0))
        await storage.write(MetricSample(name="m", timestamp=2.0, value=2.0))

        await storage.clear()

        assert await storage.count() == 0

    @pytest.mark.storage
    async def test_base_class_delete_before(self) -> None:
        """Base class delete_before removes old items."""
        storage: InMemoryStorage[LogEntry] = InMemoryStorage()
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="old"))
        await storage.write(LogEntry(timestamp=200.0, level="INFO", message="new"))

        deleted = await storage.delete_before(150.0)

        assert deleted == 1
        assert await storage.count() == 1

    @pytest.mark.storage
    def test_base_class_read_since_filters_and_sorts(self) -> None:
        """_read_since helper filters by timestamp and sorts ascending."""
        storage: InMemoryStorage[LogEntry] = InMemoryStorage()
        storage.write_sync(LogEntry(timestamp=300.0, level="INFO", message="third"))
        storage.write_sync(LogEntry(timestamp=100.0, level="INFO", message="first"))
        storage.write_sync(LogEntry(timestamp=200.0, level="INFO", message="second"))

        result = storage._read_since(since=150.0)

        assert len(result) == 2
        assert result[0].timestamp == 200.0
        assert result[1].timestamp == 300.0

    @pytest.mark.storage
    def test_base_class_sync_methods(self) -> None:
        """Sync write methods work correctly."""
        storage: InMemoryStorage[MetricSample] = InMemoryStorage()
        sample1 = MetricSample(name="m", timestamp=1.0, value=1.0)
        sample2 = MetricSample(name="m", timestamp=2.0, value=2.0)

        storage.write_sync(sample1)
        storage.write_sync_batch([sample2])

        assert len(storage._items) == 2

    @pytest.mark.storage
    def test_base_class_clear_sync(self) -> None:
        """Sync clear method works correctly."""
        storage: InMemoryStorage[LogEntry] = InMemoryStorage()
        storage.write_sync(LogEntry(timestamp=1.0, level="INFO", message="test"))

        storage.clear_sync()

        assert len(storage._items) == 0
