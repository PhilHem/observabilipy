"""Tests for SQLite metrics storage cross-instance persistence."""

from pathlib import Path

import pytest

from observabilipy.adapters.storage import SQLiteMetricsStorage
from observabilipy.core.models import MetricSample

# All tests in this module are tier 2 (integration tests with file I/O)
pytestmark = pytest.mark.tier(2)


@pytest.mark.tra("Adapter.SQLiteStorage.PersistsAcrossInstances")
class TestSQLiteMetricsPersistence:
    """Tests for metrics data persistence across storage instances."""

    @pytest.mark.storage
    async def test_metrics_data_persists_across_instances(self, tmp_path: Path) -> None:
        """Metric samples persist in file and are readable by new instances."""
        db_path = str(tmp_path / "persist_metrics.db")

        # Write with first instance
        storage1 = SQLiteMetricsStorage(db_path)
        sample = MetricSample(name="requests_total", timestamp=1000.0, value=42.0)
        await storage1.write(sample)

        # Read with second instance
        storage2 = SQLiteMetricsStorage(db_path)
        result = [s async for s in storage2.read()]

        assert result == [sample]
