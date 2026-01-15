"""Tests for SQLite log storage adapter."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from observabilipy.adapters.storage.sqlite import SQLiteLogStorage
from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.fixture
def log_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for log storage tests."""
    return str(tmp_path / "logs.db")


@pytest.fixture
async def memory_log_storage() -> AsyncGenerator[SQLiteLogStorage]:
    """In-memory log storage with proper cleanup."""
    storage = SQLiteLogStorage(":memory:")
    yield storage
    await storage.close()


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
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


@pytest.mark.tra("Adapter.SQLiteStorage.PersistsAcrossInstances")
class TestSQLiteLogPersistence:
    """Tests for log data persistence across storage instances."""

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
