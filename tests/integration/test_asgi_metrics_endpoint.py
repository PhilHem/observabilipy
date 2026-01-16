"""Integration tests for ASGI /metrics endpoints."""

import json
from collections.abc import AsyncGenerator

import pytest

from observabilipy.adapters.frameworks.asgi import create_asgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import MetricSample


@pytest.fixture
async def metrics_storage_with_data() -> AsyncGenerator[InMemoryMetricsStorage]:
    """Fixture providing a metrics storage with sample data."""
    storage = InMemoryMetricsStorage()
    await storage.write(
        MetricSample(
            name="http_requests_total",
            value=42.0,
            timestamp=1000.0,
            labels={"method": "GET", "status": "200"},
        )
    )
    return storage


class TestASGIMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_endpoint_returns_200(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics returns HTTP 200."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics")

        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointContentType")
    @pytest.mark.asgi
    async def test_metrics_endpoint_has_ndjson_content_type(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics returns correct Content-Type header."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointNDJSON")
    @pytest.mark.asgi
    async def test_metrics_endpoint_returns_ndjson_format(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage_with_data: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics returns data in NDJSON format."""
        app = create_asgi_app(log_storage, metrics_storage_with_data)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics")

        parsed = json.loads(response.text.strip())
        assert parsed["name"] == "http_requests_total"
        assert parsed["value"] == 42.0
        assert parsed["labels"] == {"method": "GET", "status": "200"}

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_metrics_endpoint_filters_by_since(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics?since=X filters samples by timestamp."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=100.0, value=1.0)
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=200.0, value=2.0)
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics?since=150")

        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["value"] == 2.0

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_empty_storage_returns_empty_body(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics returns empty body when storage is empty."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_metrics_endpoint_handles_invalid_since_param(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics handles invalid since param gracefully."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=100.0, value=1.0)
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics?since=invalid")

        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["value"] == 1.0


class TestASGIMetricsPrometheusEndpoint:
    """Tests for the /metrics/prometheus endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_prometheus_endpoint_returns_200(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics/prometheus returns HTTP 200."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics/prometheus")

        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointContentType")
    @pytest.mark.asgi
    async def test_metrics_prometheus_has_correct_content_type(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics/prometheus returns correct Content-Type header."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics/prometheus")

        expected_content_type = "text/plain; version=0.0.4; charset=utf-8"
        assert response.headers["content-type"] == expected_content_type

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointFormat")
    @pytest.mark.asgi
    async def test_metrics_prometheus_returns_prometheus_format(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage_with_data: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics/prometheus returns data in Prometheus format."""
        app = create_asgi_app(log_storage, metrics_storage_with_data)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics/prometheus")

        assert "http_requests_total" in response.text
        assert "42" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointCurrent")
    @pytest.mark.asgi
    async def test_metrics_prometheus_uses_encode_current(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics/prometheus keeps only latest sample per metric."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=100.0, value=1.0, labels={})
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=200.0, value=5.0, labels={})
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics/prometheus")

        lines = [line for line in response.text.strip().split("\n") if line]
        assert len(lines) == 1  # Only latest sample
        assert "5.0" in lines[0]

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_prometheus_empty_storage_returns_empty_body(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics/prometheus returns empty body when storage is empty."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.text == ""
