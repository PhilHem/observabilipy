"""Tests for SQLite log storage level filtering operations."""

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage
from observabilipy.core.models import LogEntry

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.LevelFiltering")
class TestSQLiteLogStorageLevelFiltering:
    """Tests for SQLite log storage level filtering operations."""

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
