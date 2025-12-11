"""Integration tests for Django adapter."""

import json
import sys

import pytest

django = pytest.importorskip("django", reason="django not installed")
from django.conf import settings
from django.test import AsyncClient

from observability.adapters.frameworks.django import create_observability_urlpatterns
from observability.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observability.core.models import LogEntry, MetricSample

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        ROOT_URLCONF=__name__,
        DATABASES={},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()


# Module-level storage instances that fixtures will reset
_log_storage: InMemoryLogStorage = InMemoryLogStorage()
_metrics_storage: InMemoryMetricsStorage = InMemoryMetricsStorage()

# Initial URL patterns
urlpatterns = create_observability_urlpatterns(_log_storage, _metrics_storage)


@pytest.fixture(autouse=True)
def reset_storage() -> None:
    """Reset storage instances before each test."""
    global _log_storage, _metrics_storage, urlpatterns
    _log_storage = InMemoryLogStorage()
    _metrics_storage = InMemoryMetricsStorage()
    # Update urlpatterns to use fresh storage
    new_patterns = create_observability_urlpatterns(_log_storage, _metrics_storage)
    # Update module-level urlpatterns via sys.modules
    current_module = sys.modules[__name__]
    current_module.urlpatterns = new_patterns  # type: ignore[attr-defined]
    # Clear Django's URL cache to pick up new patterns
    from django.urls import clear_url_caches

    clear_url_caches()


@pytest.fixture
def log_storage() -> InMemoryLogStorage:
    """Provide the current log storage instance."""
    return _log_storage


@pytest.fixture
def metrics_storage() -> InMemoryMetricsStorage:
    """Provide the current metrics storage instance."""
    return _metrics_storage


class TestDjangoMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.django
    async def test_metrics_endpoint_returns_prometheus_format(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint returns data in Prometheus text format."""
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "path": "/api"},
            )
        )

        client = AsyncClient()
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert (
            'http_requests_total{method="GET",path="/api"} 42.0'
            in response.content.decode()
        )

    @pytest.mark.django
    async def test_metrics_endpoint_content_type(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint returns correct content type for Prometheus."""
        client = AsyncClient()
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response["Content-Type"]
        assert "version=0.0.4" in response["Content-Type"]

    @pytest.mark.django
    async def test_metrics_endpoint_empty_storage(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint returns empty body when no metrics."""
        client = AsyncClient()
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.content.decode() == ""


class TestDjangoLogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.django
    async def test_logs_endpoint_returns_ndjson(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns data in NDJSON format."""
        await log_storage.write(
            LogEntry(
                timestamp=1702300000.0,
                level="INFO",
                message="Application started",
            )
        )

        client = AsyncClient()
        response = await client.get("/logs")

        assert response.status_code == 200
        parsed = json.loads(response.content.decode().strip())
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Application started"

    @pytest.mark.django
    async def test_logs_endpoint_content_type(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns correct content type for NDJSON."""
        client = AsyncClient()
        response = await client.get("/logs")

        assert response.status_code == 200
        assert "application/x-ndjson" in response["Content-Type"]

    @pytest.mark.django
    async def test_logs_endpoint_empty_storage(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns empty body when no logs."""
        client = AsyncClient()
        response = await client.get("/logs")

        assert response.status_code == 200
        assert response.content.decode() == ""

    @pytest.mark.django
    async def test_logs_endpoint_since_parameter(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint filters by since parameter."""
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="INFO", message="Old log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="INFO", message="New log")
        )

        client = AsyncClient()
        response = await client.get("/logs", {"since": "1702300001.0"})

        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["message"] == "New log"
