"""E2E tests for SQLite persistence and data durability.

Tests that data persists across storage recreations (simulating app restarts).
"""

import json

import httpx
import pytest
from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.sqlite import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.core.models import LogEntry, MetricSample, RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime


@pytest.mark.e2e
class TestSQLiteLogPersistence:
    """Test that logs persist in SQLite across storage recreations."""

    async def test_logs_persist_after_storage_recreation(
        self,
        sqlite_log_db_path: str,
    ) -> None:
        """Logs written survive storage instance recreation."""
        # Write with first storage instance
        storage1 = SQLiteLogStorage(sqlite_log_db_path)
        await storage1.write(
            LogEntry(
                timestamp=1000.0,
                level="INFO",
                message="Persisted message",
                attributes={"key": "value"},
            )
        )

        # Create new storage instance (simulating app restart)
        storage2 = SQLiteLogStorage(sqlite_log_db_path)
        entries = [e async for e in storage2.read()]

        assert len(entries) == 1
        assert entries[0].message == "Persisted message"
        assert entries[0].attributes["key"] == "value"

    async def test_logs_endpoint_after_restart(
        self,
        sqlite_log_db_path: str,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Logs are accessible via HTTP after storage recreation."""
        # Write logs with first app instance
        log_storage1 = SQLiteLogStorage(sqlite_log_db_path)
        await log_storage1.write(
            LogEntry(
                timestamp=1000.0,
                level="ERROR",
                message="Error before restart",
                attributes={},
            )
        )

        # Create new app instance (simulating restart)
        log_storage2 = SQLiteLogStorage(sqlite_log_db_path)
        metrics_storage2 = SQLiteMetricsStorage(sqlite_metrics_db_path)
        app = FastAPI()
        app.include_router(create_observability_router(log_storage2, metrics_storage2))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/logs")

        entry = json.loads(response.text.strip())
        assert entry["message"] == "Error before restart"


@pytest.mark.e2e
class TestSQLiteMetricsPersistence:
    """Test that metrics persist in SQLite across storage recreations."""

    async def test_metrics_persist_after_storage_recreation(
        self,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Metrics written survive storage instance recreation."""
        # Write with first storage instance
        storage1 = SQLiteMetricsStorage(sqlite_metrics_db_path)
        await storage1.write(
            MetricSample(
                name="persistent_counter",
                timestamp=1000.0,
                value=42.0,
                labels={"env": "test"},
            )
        )

        # Create new storage instance (simulating app restart)
        storage2 = SQLiteMetricsStorage(sqlite_metrics_db_path)
        samples = [s async for s in storage2.read()]

        assert len(samples) == 1
        assert samples[0].name == "persistent_counter"
        assert samples[0].value == 42.0
        assert samples[0].labels["env"] == "test"

    async def test_metrics_endpoint_after_restart(
        self,
        sqlite_log_db_path: str,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Metrics are accessible via HTTP after storage recreation."""
        # Write metrics with first app instance
        metrics_storage1 = SQLiteMetricsStorage(sqlite_metrics_db_path)
        await metrics_storage1.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=1000.0,
                labels={"method": "POST"},
            )
        )

        # Create new app instance (simulating restart)
        log_storage2 = SQLiteLogStorage(sqlite_log_db_path)
        metrics_storage2 = SQLiteMetricsStorage(sqlite_metrics_db_path)
        app = FastAPI()
        app.include_router(create_observability_router(log_storage2, metrics_storage2))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/metrics")

        assert "http_requests_total" in response.text
        assert "1000" in response.text


@pytest.mark.e2e
class TestRetentionCleanup:
    """Test that EmbeddedRuntime properly cleans up old data."""

    async def test_age_based_retention_removes_old_logs(
        self,
        sqlite_log_db_path: str,
    ) -> None:
        """Old logs are removed based on age retention policy."""
        storage = SQLiteLogStorage(sqlite_log_db_path)
        current_time = 1000.0

        # Write old and new logs
        await storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="old", attributes={})
        )
        await storage.write(
            LogEntry(timestamp=current_time, level="INFO", message="new", attributes={})
        )

        # Run retention with max_age_seconds=500
        # This means entries older than current_time - 500 = 500.0 should be deleted
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=RetentionPolicy(max_age_seconds=500),
            time_func=lambda: current_time,
        )
        await runtime.run_once()

        entries = [e async for e in storage.read()]
        assert len(entries) == 1
        assert entries[0].message == "new"

    async def test_age_based_retention_removes_old_metrics(
        self,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Old metrics are removed based on age retention policy."""
        storage = SQLiteMetricsStorage(sqlite_metrics_db_path)
        current_time = 1000.0

        # Write old and new metrics
        await storage.write(
            MetricSample(name="old_metric", timestamp=100.0, value=1.0, labels={})
        )
        await storage.write(
            MetricSample(
                name="new_metric", timestamp=current_time, value=2.0, labels={}
            )
        )

        runtime = EmbeddedRuntime(
            metrics_storage=storage,
            metrics_retention=RetentionPolicy(max_age_seconds=500),
            time_func=lambda: current_time,
        )
        await runtime.run_once()

        samples = [s async for s in storage.read()]
        assert len(samples) == 1
        assert samples[0].name == "new_metric"

    async def test_count_based_retention_keeps_only_max_count(
        self,
        sqlite_log_db_path: str,
    ) -> None:
        """Count-based retention keeps only the newest entries."""
        storage = SQLiteLogStorage(sqlite_log_db_path)

        # Write 5 log entries
        for i in range(5):
            await storage.write(
                LogEntry(
                    timestamp=float(i * 100),
                    level="INFO",
                    message=f"message_{i}",
                    attributes={},
                )
            )

        # Run retention with max_count=3
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=RetentionPolicy(max_count=3),
        )
        await runtime.run_once()

        entries = [e async for e in storage.read()]
        # Should keep the 3 newest (highest timestamps)
        assert len(entries) == 3
        messages = [e.message for e in entries]
        assert "message_2" in messages
        assert "message_3" in messages
        assert "message_4" in messages
        assert "message_0" not in messages
        assert "message_1" not in messages


@pytest.mark.e2e
class TestFullLifecycleWithRetention:
    """Test complete lifecycle: write → cleanup → read via HTTP."""

    async def test_full_lifecycle_with_retention(
        self,
        sqlite_log_db_path: str,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Full lifecycle with storage, runtime, and HTTP endpoints."""
        log_storage = SQLiteLogStorage(sqlite_log_db_path)
        metrics_storage = SQLiteMetricsStorage(sqlite_metrics_db_path)
        current_time = 1000.0

        # Write a mix of old and new data
        await log_storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="old_log", attributes={})
        )
        await log_storage.write(
            LogEntry(
                timestamp=current_time, level="INFO", message="new_log", attributes={}
            )
        )
        await metrics_storage.write(
            MetricSample(name="old_metric", timestamp=100.0, value=1.0, labels={})
        )
        await metrics_storage.write(
            MetricSample(
                name="new_metric", timestamp=current_time, value=2.0, labels={}
            )
        )

        # Run retention cleanup
        runtime = EmbeddedRuntime(
            log_storage=log_storage,
            log_retention=RetentionPolicy(max_age_seconds=500),
            metrics_storage=metrics_storage,
            metrics_retention=RetentionPolicy(max_age_seconds=500),
            time_func=lambda: current_time,
        )
        await runtime.run_once()

        # Verify via HTTP endpoints
        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            logs_response = await client.get("/logs")
            metrics_response = await client.get("/metrics")

        # Old data should be gone, new data should remain
        assert "old_log" not in logs_response.text
        assert "new_log" in logs_response.text
        assert "old_metric" not in metrics_response.text
        assert "new_metric" in metrics_response.text
