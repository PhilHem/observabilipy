"""Tests for SQLite metrics storage error handling and resilience."""

import sqlite3
from pathlib import Path

import pytest

from observabilipy.adapters.storage import SQLiteMetricsStorage
from observabilipy.core.models import MetricSample

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.ImplementsMetricsStoragePort")
class TestSQLiteMetricsStorageResilience:
    """Tests for handling corrupted JSON in metrics storage."""

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsMetricsStoragePort")
    @pytest.mark.storage
    async def test_read_handles_corrupted_labels_json(self, tmp_path: Path) -> None:
        """Read falls back to empty dict when labels JSON is corrupted."""
        db_path = str(tmp_path / "corrupt_metrics.db")
        storage = SQLiteMetricsStorage(db_path)

        # Write a valid sample first to initialize schema
        valid_sample = MetricSample(
            name="valid_metric",
            timestamp=1000.0,
            value=42.0,
            labels={"key": "value"},
        )
        await storage.write(valid_sample)

        # Inject corrupted JSON directly via SQL
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO metrics (name, timestamp, value, labels) VALUES (?, ?, ?, ?)",
            ("corrupted_metric", 2000.0, 99.0, "not valid json{"),
        )
        conn.commit()
        conn.close()

        # Read should succeed, corrupted sample gets empty labels
        result = [s async for s in storage.read()]

        assert len(result) == 2
        assert result[0].labels == {"key": "value"}  # Valid sample
        assert result[1].labels == {}  # Corrupted sample falls back to empty dict
        assert result[1].name == "corrupted_metric"

    @pytest.mark.tra("Adapter.SQLiteStorage.ImplementsMetricsStoragePort")
    @pytest.mark.storage
    def test_read_sync_handles_corrupted_labels_json(self, tmp_path: Path) -> None:
        """Sync read falls back to empty dict when labels JSON is corrupted."""
        db_path = str(tmp_path / "corrupt_metrics_sync.db")
        storage = SQLiteMetricsStorage(db_path)

        # Write a valid sample first to initialize schema
        valid_sample = MetricSample(
            name="valid_metric",
            timestamp=1000.0,
            value=42.0,
            labels={"key": "value"},
        )
        storage.write_sync(valid_sample)

        # Inject corrupted JSON directly via SQL
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO metrics (name, timestamp, value, labels) VALUES (?, ?, ?, ?)",
            ("corrupted_metric", 2000.0, 99.0, "not valid json{"),
        )
        conn.commit()
        conn.close()

        # Read should succeed, corrupted sample gets empty labels
        result = storage.read_sync()

        assert len(result) == 2
        assert result[0].labels == {"key": "value"}  # Valid sample
        assert result[1].labels == {}  # Corrupted sample falls back to empty dict
        assert result[1].name == "corrupted_metric"
