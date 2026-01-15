"""Tests for LogStorageWithLevelFilter domain service."""

import pytest

from observabilipy.adapters.storage.in_memory import InMemoryLogStorage
from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort
from observabilipy.core.services import LogStorageWithLevelFilter

pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.tra("Core.LogStorageWithLevelFilter.DomainFiltering"),
]


class TestLogStorageWithLevelFilter:
    """Tests for LogStorageWithLevelFilter domain service."""

    @pytest.mark.core
    def test_implements_log_storage_port(self) -> None:
        """LogStorageWithLevelFilter must satisfy LogStoragePort protocol."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        assert isinstance(wrapper, LogStoragePort)

    @pytest.mark.core
    async def test_filter_by_level_returns_matching_entries(self) -> None:
        """filter_by_level returns only entries matching the specified level."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info")
        await wrapper.write(error_entry)
        await wrapper.write(info_entry)

        result = [e async for e in wrapper.filter_by_level("ERROR")]

        assert result == [error_entry]

    @pytest.mark.core
    async def test_filter_by_level_case_insensitive(self) -> None:
        """filter_by_level matches level case-insensitively."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error")
        await wrapper.write(error_entry)

        result = [e async for e in wrapper.filter_by_level("error")]

        assert result == [error_entry]

    @pytest.mark.core
    async def test_filter_by_level_with_since(self) -> None:
        """filter_by_level respects since parameter."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        old_error = LogEntry(timestamp=1000.0, level="ERROR", message="old")
        new_error = LogEntry(timestamp=2000.0, level="ERROR", message="new")
        await wrapper.write(old_error)
        await wrapper.write(new_error)

        result = [e async for e in wrapper.filter_by_level("ERROR", since=1500.0)]

        assert result == [new_error]

    @pytest.mark.core
    async def test_count_by_level_returns_correct_count(self) -> None:
        """count_by_level returns count for specified level only."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="ERROR", message="e1"))
        await wrapper.write(LogEntry(timestamp=101.0, level="ERROR", message="e2"))
        await wrapper.write(LogEntry(timestamp=102.0, level="INFO", message="i1"))

        count = await wrapper.count_by_level("ERROR")

        assert count == 2

    @pytest.mark.core
    async def test_count_by_level_empty_returns_zero(self) -> None:
        """count_by_level returns 0 for non-existent level."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        count = await wrapper.count_by_level("ERROR")

        assert count == 0

    @pytest.mark.core
    async def test_delete_by_level_before_removes_matching(self) -> None:
        """delete_by_level_before removes entries matching level and timestamp."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="ERROR", message="old"))
        await wrapper.write(LogEntry(timestamp=200.0, level="ERROR", message="new"))
        await wrapper.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        deleted = await wrapper.delete_by_level_before("ERROR", 150.0)

        assert deleted == 1
        entries = [e async for e in wrapper.read()]
        assert len(entries) == 2

    @pytest.mark.core
    async def test_delete_by_level_before_preserves_others(self) -> None:
        """delete_by_level_before does not affect other levels."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="ERROR", message="error"))
        await wrapper.write(LogEntry(timestamp=100.0, level="INFO", message="info"))

        await wrapper.delete_by_level_before("ERROR", 150.0)

        entries = [e async for e in wrapper.read()]
        assert len(entries) == 1
        assert entries[0].level == "INFO"


class TestLogStorageWithLevelFilterPassthrough:
    """Tests for pass-through delegation to underlying storage."""

    @pytest.mark.core
    async def test_passthrough_write(self) -> None:
        """write() delegates to underlying storage."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")

        await wrapper.write(entry)

        # Verify entry is in underlying storage
        result = [e async for e in storage.read()]
        assert result == [entry]

    @pytest.mark.core
    async def test_passthrough_write_sync(self) -> None:
        """write_sync() delegates to underlying storage."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")

        wrapper.write_sync(entry)

        result = [e async for e in storage.read()]
        assert result == [entry]

    @pytest.mark.core
    async def test_passthrough_read_without_level(self) -> None:
        """read() without level returns all entries."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")
        await wrapper.write(entry)

        result = [e async for e in wrapper.read()]

        assert result == [entry]

    @pytest.mark.core
    async def test_passthrough_read_with_level(self) -> None:
        """read() with level filters entries."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        error_entry = LogEntry(timestamp=1000.0, level="ERROR", message="error")
        info_entry = LogEntry(timestamp=1001.0, level="INFO", message="info")
        await wrapper.write(error_entry)
        await wrapper.write(info_entry)

        result = [e async for e in wrapper.read(level="ERROR")]

        assert result == [error_entry]

    @pytest.mark.core
    async def test_passthrough_count(self) -> None:
        """count() delegates to underlying storage."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="INFO", message="1"))
        await wrapper.write(LogEntry(timestamp=101.0, level="INFO", message="2"))

        count = await wrapper.count()

        assert count == 2

    @pytest.mark.core
    async def test_passthrough_delete_before(self) -> None:
        """delete_before() delegates to underlying storage."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="INFO", message="old"))
        await wrapper.write(LogEntry(timestamp=200.0, level="INFO", message="new"))

        deleted = await wrapper.delete_before(150.0)

        assert deleted == 1
        assert await wrapper.count() == 1

    @pytest.mark.core
    async def test_passthrough_clear(self) -> None:
        """clear() delegates to underlying storage."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        await wrapper.write(LogEntry(timestamp=100.0, level="INFO", message="1"))
        await wrapper.write(LogEntry(timestamp=101.0, level="INFO", message="2"))

        await wrapper.clear()

        assert await wrapper.count() == 0

    @pytest.mark.core
    def test_passthrough_clear_sync(self) -> None:
        """clear_sync() delegates to underlying storage."""
        storage = InMemoryLogStorage()
        wrapper = LogStorageWithLevelFilter(storage)
        wrapper.write_sync(LogEntry(timestamp=100.0, level="INFO", message="1"))

        wrapper.clear_sync()

        assert storage._entries == []
