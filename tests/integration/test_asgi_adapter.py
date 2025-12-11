"""Integration tests for ASGI generic adapter."""

import httpx
import pytest

from observability.adapters.frameworks.asgi import create_asgi_app
from observability.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observability.core.models import LogEntry, MetricSample


class TestASGIMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.asgi
    async def test_metrics_endpoint_returns_200(self) -> None:
        """Test that /metrics returns HTTP 200."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        assert response.status_code == 200

    @pytest.mark.asgi
    async def test_metrics_endpoint_has_prometheus_content_type(self) -> None:
        """Test that /metrics returns correct Content-Type header."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        expected_content_type = "text/plain; version=0.0.4; charset=utf-8"
        assert response.headers["content-type"] == expected_content_type

    @pytest.mark.asgi
    async def test_metrics_endpoint_returns_prometheus_format(self) -> None:
        """Test that /metrics returns data in Prometheus format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                value=42.0,
                timestamp=1000.0,
                labels={"method": "GET", "status": "200"},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        assert "http_requests_total" in response.text
        assert "42" in response.text


class TestASGILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.asgi
    async def test_logs_endpoint_returns_200(self) -> None:
        """Test that /logs returns HTTP 200."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert response.status_code == 200

    @pytest.mark.asgi
    async def test_logs_endpoint_has_ndjson_content_type(self) -> None:
        """Test that /logs returns correct Content-Type header."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.asgi
    async def test_logs_endpoint_returns_ndjson_format(self) -> None:
        """Test that /logs returns data in NDJSON format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(
                timestamp=1000.0,
                level="INFO",
                message="Test message",
                attributes={"key": "value"},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert "Test message" in response.text
        assert "INFO" in response.text

    @pytest.mark.asgi
    async def test_logs_endpoint_filters_by_since(self) -> None:
        """Test that /logs?since=X filters entries by timestamp."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Old message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="INFO",
                message="New message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?since=150")

        assert "New message" in response.text
        assert "Old message" not in response.text


class TestASGIRouting:
    """Tests for routing and error handling."""

    @pytest.mark.asgi
    async def test_unknown_path_returns_404(self) -> None:
        """Test that unknown paths return HTTP 404."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/unknown")

        assert response.status_code == 404


class TestASGIEmptyStorage:
    """Tests for edge cases with empty storage."""

    @pytest.mark.asgi
    async def test_metrics_empty_storage_returns_empty_body(self) -> None:
        """Test that /metrics returns empty body when storage is empty."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.asgi
    async def test_logs_empty_storage_returns_empty_body(self) -> None:
        """Test that /logs returns empty body when storage is empty."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""
