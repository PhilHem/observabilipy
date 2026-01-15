"""Tests for SQLite log storage persistence across instances."""

from pathlib import Path

import pytest

from observabilipy.adapters.storage import SQLiteLogStorage
from observabilipy.core.models import LogEntry

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


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
