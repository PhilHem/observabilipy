"""Tests for ring buffer log storage adapter."""

import pytest

from observabilipy.adapters.storage.ring_buffer import RingBufferLogStorage
from observabilipy.core.exceptions import ConfigurationError
from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort

# Unit tests - in-memory only, no I/O
pytestmark = pytest.mark.tier(1)


@pytest.mark.tra("Adapter.RingBufferStorage.ImplementsLogStoragePort")
class TestRingBufferLogStorage:
    """Tests for RingBufferLogStorage adapter."""

    @pytest.mark.storage
    def test_rejects_zero_max_size(self) -> None:
        """max_size=0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            RingBufferLogStorage(max_size=0)
        assert "max_size" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    @pytest.mark.storage
    def test_rejects_negative_max_size(self) -> None:
        """Negative max_size raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            RingBufferLogStorage(max_size=-1)

    @pytest.mark.storage
    def test_implements_log_storage_port(self) -> None:
        """RingBufferLogStorage must satisfy LogStoragePort protocol."""
        storage = RingBufferLogStorage(max_size=100)
        assert isinstance(storage, LogStoragePort)

    @pytest.mark.storage
    async def test_write_and_read_single_entry(self) -> None:
        """Can write a log entry and read it back."""
        storage = RingBufferLogStorage(max_size=100)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test message")

        await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result == [entry]

    @pytest.mark.storage
    async def test_read_returns_empty_when_no_entries(self) -> None:
        """Read returns empty iterable when storage is empty."""
        storage = RingBufferLogStorage(max_size=100)

        result = [e async for e in storage.read()]

        assert result == []

    @pytest.mark.storage
    async def test_read_filters_by_since_timestamp(self) -> None:
        """Read only returns entries with timestamp > since."""
        storage = RingBufferLogStorage(max_size=100)
        old_entry = LogEntry(timestamp=1000.0, level="INFO", message="old")
        new_entry = LogEntry(timestamp=2000.0, level="INFO", message="new")

        await storage.write(old_entry)
        await storage.write(new_entry)
        result = [e async for e in storage.read(since=1000.0)]

        assert result == [new_entry]

    @pytest.mark.storage
    async def test_read_returns_entries_ordered_by_timestamp(self) -> None:
        """Read returns entries ordered by timestamp ascending."""
        storage = RingBufferLogStorage(max_size=100)
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
        storage = RingBufferLogStorage(max_size=100)
        entries = [
            LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            for i in range(5)
        ]

        for entry in entries:
            await storage.write(entry)
        result = [e async for e in storage.read()]

        assert result == entries

    @pytest.mark.storage
    async def test_evicts_oldest_entries_when_full(self) -> None:
        """Oldest entries are evicted when buffer exceeds max_size."""
        storage = RingBufferLogStorage(max_size=3)
        entries = [
            LogEntry(timestamp=float(i), level="INFO", message=f"msg {i}")
            for i in range(5)  # Write 5 entries to buffer of size 3
        ]

        for entry in entries:
            await storage.write(entry)
        result = [e async for e in storage.read()]

        # Only last 3 should remain (entries[2], entries[3], entries[4])
        assert result == entries[2:]

    @pytest.mark.storage
    async def test_count_returns_zero_when_empty(self) -> None:
        """Count returns 0 for empty storage."""
        storage = RingBufferLogStorage(max_size=100)

        count = await storage.count()

        assert count == 0

    @pytest.mark.storage
    async def test_count_returns_correct_count_after_writes(self) -> None:
        """Count returns correct number of entries after writes."""
        storage = RingBufferLogStorage(max_size=100)
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            )

        count = await storage.count()

        assert count == 5

    @pytest.mark.storage
    async def test_delete_before_removes_old_entries(self) -> None:
        """delete_before removes entries with timestamp < given value."""
        storage = RingBufferLogStorage(max_size=100)
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
        storage = RingBufferLogStorage(max_size=100)
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
        storage = RingBufferLogStorage(max_size=100)
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            )

        deleted = await storage.delete_before(1003.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_before_empty_storage(self) -> None:
        """delete_before on empty storage returns 0."""
        storage = RingBufferLogStorage(max_size=100)

        deleted = await storage.delete_before(1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_delete_by_level_before_removes_matching_entries(self) -> None:
        """delete_by_level_before removes entries matching level and timestamp."""
        storage = RingBufferLogStorage(max_size=100)
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
        storage = RingBufferLogStorage(max_size=100)
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error"))
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        await storage.delete_by_level_before("ERROR", 150.0)

        entries = [e async for e in storage.read()]
        assert len(entries) == 1
        assert entries[0].level == "INFO"

    @pytest.mark.storage
    async def test_delete_by_level_before_returns_deleted_count(self) -> None:
        """delete_by_level_before returns number of entries deleted."""
        storage = RingBufferLogStorage(max_size=100)
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=100.0 + i, level="DEBUG", message=f"msg {i}")
            )

        deleted = await storage.delete_by_level_before("DEBUG", 103.0)

        assert deleted == 3

    @pytest.mark.storage
    async def test_delete_by_level_before_empty_storage(self) -> None:
        """delete_by_level_before on empty storage returns 0."""
        storage = RingBufferLogStorage(max_size=100)

        deleted = await storage.delete_by_level_before("ERROR", 1000.0)

        assert deleted == 0

    @pytest.mark.storage
    async def test_count_by_level_returns_count_for_specific_level(self) -> None:
        """count_by_level returns count only for specified level."""
        storage = RingBufferLogStorage(max_size=100)
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error 1"))
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="error 2"))
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await storage.count_by_level("ERROR")

        assert count == 2

    @pytest.mark.storage
    async def test_count_by_level_returns_zero_for_absent_level(self) -> None:
        """count_by_level returns 0 when no entries match level."""
        storage = RingBufferLogStorage(max_size=100)
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await storage.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.storage
    async def test_count_by_level_empty_storage(self) -> None:
        """count_by_level on empty storage returns 0."""
        storage = RingBufferLogStorage(max_size=100)

        count = await storage.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.storage
    async def test_read_filters_by_level(self) -> None:
        """Read with level parameter returns only matching entries."""
        storage = RingBufferLogStorage(max_size=100)
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
        storage = RingBufferLogStorage(max_size=100)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        result = [e async for e in storage.read(level=None)]

        assert result == [error_entry, info_entry]

    @pytest.mark.storage
    async def test_read_level_filter_is_case_insensitive(self) -> None:
        """Read level filter matches regardless of case."""
        storage = RingBufferLogStorage(max_size=100)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error msg")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info msg")

        await storage.write(error_entry)
        await storage.write(info_entry)
        result = [e async for e in storage.read(level="error")]

        assert result == [error_entry]

    @pytest.mark.storage
    async def test_read_combines_since_and_level_filters(self) -> None:
        """Read combines both since and level filters."""
        storage = RingBufferLogStorage(max_size=100)
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
        storage = RingBufferLogStorage(max_size=100)
        info_entry = LogEntry(timestamp=1000.0, level="INFO", message="info msg")

        await storage.write(info_entry)
        result = [e async for e in storage.read(level="FATAL")]

        assert result == []


@pytest.mark.tra("Adapter.RingBufferStorage.ImplementsLogStoragePort")
class TestRingBufferLogStorageSync:
    """Tests for synchronous methods on RingBufferLogStorage."""

    @pytest.mark.storage
    def test_write_sync_writes_single_entry(self) -> None:
        """write_sync() appends a single entry synchronously."""
        storage = RingBufferLogStorage(max_size=100)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")

        storage.write_sync(entry)

        assert len(storage._buffer) == 1
        assert storage._buffer[0] == entry

    @pytest.mark.storage
    def test_write_sync_respects_max_size(self) -> None:
        """write_sync() evicts oldest entry when buffer is full."""
        storage = RingBufferLogStorage(max_size=2)
        entries = [
            LogEntry(timestamp=float(i), level="INFO", message=f"msg {i}")
            for i in range(3)
        ]

        for entry in entries:
            storage.write_sync(entry)

        assert len(storage._buffer) == 2
        assert list(storage._buffer) == entries[1:]

    @pytest.mark.storage
    async def test_clear_removes_all_entries(self) -> None:
        """clear() removes all entries from storage."""
        storage = RingBufferLogStorage(max_size=100)
        await storage.write(LogEntry(timestamp=1000.0, level="INFO", message="first"))
        await storage.write(LogEntry(timestamp=1001.0, level="DEBUG", message="second"))

        await storage.clear()

        assert await storage.count() == 0

    @pytest.mark.storage
    def test_clear_sync_removes_all_entries(self) -> None:
        """clear_sync() removes all entries synchronously."""
        storage = RingBufferLogStorage(max_size=100)
        storage.write_sync(LogEntry(timestamp=1000.0, level="INFO", message="first"))
        storage.write_sync(LogEntry(timestamp=1001.0, level="DEBUG", message="second"))

        storage.clear_sync()

        assert len(storage._buffer) == 0
