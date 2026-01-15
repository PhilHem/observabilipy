"""Tests for SQLite log storage adapter synchronous methods."""

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage
from observabilipy.core.models import LogEntry

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
class TestSQLiteLogStorageSync:
    """Tests for synchronous methods on SQLiteLogStorage."""

    @pytest.mark.storage
    def test_write_sync_writes_single_entry(self, log_db_path: str) -> None:
        """write_sync() inserts a single entry synchronously."""
        storage = SQLiteLogStorage(log_db_path)
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test")

        storage.write_sync(entry)

        # Verify by reading back synchronously
        entries = storage.read_sync()
        assert entries == [entry]

    @pytest.mark.storage
    def test_write_sync_multiple_entries(self, log_db_path: str) -> None:
        """write_sync() can write multiple entries sequentially."""
        storage = SQLiteLogStorage(log_db_path)
        entries = [
            LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            for i in range(3)
        ]

        for entry in entries:
            storage.write_sync(entry)

        result = storage.read_sync()
        assert result == entries

    @pytest.mark.storage
    async def test_clear_removes_all_entries(self, log_db_path: str) -> None:
        """clear() removes all entries from storage."""
        storage = SQLiteLogStorage(log_db_path)
        await storage.write(LogEntry(timestamp=1000.0, level="INFO", message="first"))
        await storage.write(LogEntry(timestamp=1001.0, level="DEBUG", message="second"))

        await storage.clear()

        assert await storage.count() == 0

    @pytest.mark.storage
    def test_clear_sync_removes_all_entries(self, log_db_path: str) -> None:
        """clear_sync() removes all entries synchronously."""
        storage = SQLiteLogStorage(log_db_path)
        storage.write_sync(LogEntry(timestamp=1000.0, level="INFO", message="first"))
        storage.write_sync(LogEntry(timestamp=1001.0, level="DEBUG", message="second"))

        storage.clear_sync()

        entries = storage.read_sync()
        assert entries == []

    @pytest.mark.storage
    async def test_sync_and_async_share_same_file_db(self, log_db_path: str) -> None:
        """Sync and async methods share data for file-based databases."""
        storage = SQLiteLogStorage(log_db_path)
        entry_sync = LogEntry(timestamp=1000.0, level="INFO", message="sync entry")
        entry_async = LogEntry(timestamp=1001.0, level="DEBUG", message="async entry")

        # Write sync
        storage.write_sync(entry_sync)

        # Write async
        await storage.write(entry_async)

        # Read sync - should see both
        entries = storage.read_sync()
        assert len(entries) == 2
        assert entry_sync in entries
        assert entry_async in entries
