"""Tests for SQLite log storage adapter."""

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage
from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
class TestSQLiteLogStorage:
    """Tests for SQLiteLogStorage adapter."""

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
    @pytest.mark.storage
    def test_implements_log_storage_port(self) -> None:
        """SQLiteLogStorage must satisfy LogStoragePort protocol."""
        storage = SQLiteLogStorage(":memory:")
        assert isinstance(storage, LogStoragePort)

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
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

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
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

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
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

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
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
