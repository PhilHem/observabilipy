"""Integration tests for FastAPI adapter."""

import json

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from observability.adapters.frameworks.fastapi import create_observability_router
from observability.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observability.core.models import LogEntry, MetricSample


class TestFastAPIMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.fastapi
    async def test_metrics_endpoint_returns_prometheus_format(self) -> None:
        """Metrics endpoint returns data in Prometheus text format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "path": "/api"},
            )
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert 'http_requests_total{method="GET",path="/api"} 42.0' in response.text

    @pytest.mark.fastapi
    async def test_metrics_endpoint_content_type(self) -> None:
        """Metrics endpoint returns correct content type for Prometheus."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "version=0.0.4" in response.headers["content-type"]

    @pytest.mark.fastapi
    async def test_metrics_endpoint_empty_storage(self) -> None:
        """Metrics endpoint returns empty body when no metrics."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""


class TestFastAPILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.fastapi
    async def test_logs_endpoint_returns_ndjson(self) -> None:
        """Logs endpoint returns data in NDJSON format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(
                timestamp=1702300000.0,
                level="INFO",
                message="Application started",
            )
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs")

        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Application started"

    @pytest.mark.fastapi
    async def test_logs_endpoint_content_type(self) -> None:
        """Logs endpoint returns correct content type for NDJSON."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs")

        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]

    @pytest.mark.fastapi
    async def test_logs_endpoint_empty_storage(self) -> None:
        """Logs endpoint returns empty body when no logs."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.fastapi
    async def test_logs_endpoint_since_parameter(self) -> None:
        """Logs endpoint filters by since parameter."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="INFO", message="Old log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="INFO", message="New log")
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs", params={"since": 1702300001.0})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["message"] == "New log"
