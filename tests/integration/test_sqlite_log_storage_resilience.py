"""Tests for SQLite log storage resilience and error handling."""

import sqlite3
from pathlib import Path

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage
from observabilipy.core.models import LogEntry

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
class TestSQLiteLogStorageResilience:
    """Tests for handling corrupted JSON in log storage."""

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
    @pytest.mark.storage
    async def test_read_handles_corrupted_attributes_json(self, tmp_path: Path) -> None:
        """Read falls back to empty dict when attributes JSON is corrupted."""
        db_path = str(tmp_path / "corrupt_logs.db")
        storage = SQLiteLogStorage(db_path)

        # Write a valid entry first to initialize schema
        valid_entry = LogEntry(
            timestamp=1000.0, level="INFO", message="valid", attributes={"key": "value"}
        )
        await storage.write(valid_entry)

        # Inject corrupted JSON directly via SQL
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO logs (timestamp, level, message, attributes) "
            "VALUES (?, ?, ?, ?)",
            (2000.0, "ERROR", "corrupted", "not valid json{"),
        )
        conn.commit()
        conn.close()

        # Read should succeed, corrupted entry gets empty attributes
        result = [e async for e in storage.read()]

        assert len(result) == 2
        assert result[0].attributes == {"key": "value"}  # Valid entry
        assert result[1].attributes == {}  # Corrupted entry falls back to empty dict
        assert result[1].message == "corrupted"

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsLogStoragePort")
    @pytest.mark.storage
    def test_read_sync_handles_corrupted_attributes_json(self, tmp_path: Path) -> None:
        """Sync read falls back to empty dict when attributes JSON is corrupted."""
        db_path = str(tmp_path / "corrupt_logs_sync.db")
        storage = SQLiteLogStorage(db_path)

        # Write a valid entry first to initialize schema
        valid_entry = LogEntry(
            timestamp=1000.0, level="INFO", message="valid", attributes={"key": "value"}
        )
        storage.write_sync(valid_entry)

        # Inject corrupted JSON directly via SQL
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO logs (timestamp, level, message, attributes) "
            "VALUES (?, ?, ?, ?)",
            (2000.0, "ERROR", "corrupted", "not valid json{"),
        )
        conn.commit()
        conn.close()

        # Read should succeed, corrupted entry gets empty attributes
        result = storage.read_sync()

        assert len(result) == 2
        assert result[0].attributes == {"key": "value"}  # Valid entry
        assert result[1].attributes == {}  # Corrupted entry falls back to empty dict
        assert result[1].message == "corrupted"
