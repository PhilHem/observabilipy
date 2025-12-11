"""Integration tests for example files.

These tests verify that examples remain valid as interfaces evolve.
They test imports, app creation, and basic endpoint functionality.
"""

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient


@pytest.mark.examples
class TestFastAPIExample:
    """Tests for fastapi_example.py."""

    def test_app_creation(self) -> None:
        """Example app can be created and has observability endpoints."""
        from examples.fastapi_example import app

        client = TestClient(app)

        # Verify endpoints exist
        assert client.get("/metrics").status_code == 200
        assert client.get("/logs").status_code == 200

    def test_root_endpoint_records_data(self) -> None:
        """Root endpoint records metrics and logs."""
        from examples.fastapi_example import app, log_storage, metrics_storage

        client = TestClient(app)

        # Clear any existing data
        log_storage._entries.clear()
        metrics_storage._samples.clear()

        # Hit root endpoint
        response = client.get("/")
        assert response.status_code == 200

        # Verify data was recorded
        assert client.get("/logs").text != ""
        assert client.get("/metrics").text != ""


@pytest.mark.examples
class TestMinimalExample:
    """Tests for minimal_example.py."""

    def test_app_creation(self) -> None:
        """Example app can be created and has observability endpoints."""
        from examples.minimal_example import app

        client = TestClient(app)

        # Verify endpoints exist
        assert client.get("/metrics").status_code == 200
        assert client.get("/logs").status_code == 200


@pytest.mark.examples
class TestCgroupsExample:
    """Tests for cgroups_example.py."""

    def test_app_creation(self) -> None:
        """Example app can be created and has observability endpoints."""
        from examples.cgroups_example import app

        client = TestClient(app)

        # Verify endpoints exist
        assert client.get("/metrics").status_code == 200
        assert client.get("/logs").status_code == 200

    def test_cpu_tracker(self) -> None:
        """CpuTracker calculates CPU percentage."""
        from examples.cgroups_example import CpuTracker

        tracker = CpuTracker()

        # First call returns 0.0 (no previous measurement)
        result = tracker.get_cpu_percent()
        # Returns None if cgroups unavailable, 0.0 if available
        assert result is None or result == 0.0


@pytest.mark.examples
class TestSqliteExample:
    """Tests for sqlite_example.py."""

    def test_imports(self) -> None:
        """Example imports work correctly."""
        from examples.sqlite_example import (
            SQLiteLogStorage,
            SQLiteMetricsStorage,
            app,
            log_storage,
            metrics_storage,
        )

        assert isinstance(log_storage, SQLiteLogStorage)
        assert isinstance(metrics_storage, SQLiteMetricsStorage)
        assert app is not None


@pytest.mark.examples
class TestRingBufferExample:
    """Tests for ring_buffer_example.py."""

    def test_app_creation(self) -> None:
        """Example app can be created and has observability endpoints."""
        from examples.ring_buffer_example import app

        client = TestClient(app)

        # Verify endpoints exist
        assert client.get("/metrics").status_code == 200
        assert client.get("/logs").status_code == 200

    def test_storage_has_max_size(self) -> None:
        """Storage backends are configured with max_size."""
        from examples.ring_buffer_example import log_storage, metrics_storage

        assert log_storage._buffer.maxlen == 1000
        assert metrics_storage._buffer.maxlen == 1000


@pytest.mark.examples
class TestAsgiExample:
    """Tests for asgi_example.py."""

    def test_app_creation(self) -> None:
        """Example ASGI app can be created."""
        from examples.asgi_example import app, create_asgi_app

        assert app is not None
        assert callable(create_asgi_app)

    async def test_demo_data_function(self) -> None:
        """Demo data function works."""
        from examples.asgi_example import demo_data, log_storage, metrics_storage

        # Clear any existing data
        log_storage._entries.clear()
        metrics_storage._samples.clear()

        await demo_data()

        # Verify data was added
        entries = [e async for e in log_storage.read()]
        samples = [s async for s in metrics_storage.scrape()]
        assert len(entries) == 1
        assert len(samples) == 1


@pytest.mark.examples
class TestEmbeddedRuntimeExample:
    """Tests for embedded_runtime_example.py."""

    def test_imports(self) -> None:
        """Example imports work correctly."""
        from examples.embedded_runtime_example import (
            EmbeddedRuntime,
            RetentionPolicy,
            SQLiteLogStorage,
            SQLiteMetricsStorage,
            app,
            log_retention,
            log_storage,
            metrics_retention,
            metrics_storage,
            runtime,
        )

        assert isinstance(log_storage, SQLiteLogStorage)
        assert isinstance(metrics_storage, SQLiteMetricsStorage)
        assert isinstance(log_retention, RetentionPolicy)
        assert isinstance(metrics_retention, RetentionPolicy)
        assert isinstance(runtime, EmbeddedRuntime)
        assert app is not None

    def test_retention_policy_values(self) -> None:
        """Retention policies are configured correctly."""
        from examples.embedded_runtime_example import log_retention, metrics_retention

        assert log_retention.max_age_seconds == 3600
        assert metrics_retention.max_age_seconds == 3600
