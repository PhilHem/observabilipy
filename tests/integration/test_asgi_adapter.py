"""Integration tests for ASGI generic adapter."""

import json
from collections.abc import AsyncGenerator

import httpx
import pytest

from observabilipy.adapters.frameworks.asgi import create_asgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample


@pytest.fixture
async def log_storage() -> AsyncGenerator[InMemoryLogStorage]:
    """Fixture providing an empty log storage."""
    return InMemoryLogStorage()


@pytest.fixture
async def metrics_storage() -> AsyncGenerator[InMemoryMetricsStorage]:
    """Fixture providing an empty metrics storage."""
    return InMemoryMetricsStorage()


@pytest.fixture
async def log_storage_with_data() -> AsyncGenerator[InMemoryLogStorage]:
    """Fixture providing a log storage with sample data."""
    storage = InMemoryLogStorage()
    await storage.write(
        LogEntry(
            timestamp=1000.0,
            level="INFO",
            message="Test message",
            attributes={"key": "value"},
        )
    )
    return storage


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
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics returns HTTP 200."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointContentType")
    @pytest.mark.asgi
    async def test_metrics_endpoint_has_ndjson_content_type(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics returns correct Content-Type header."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointNDJSON")
    @pytest.mark.asgi
    async def test_metrics_endpoint_returns_ndjson_format(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage_with_data: InMemoryMetricsStorage,
    ) -> None:
        """Test that /metrics returns data in NDJSON format."""
        app = create_asgi_app(log_storage, metrics_storage_with_data)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        parsed = json.loads(response.text.strip())
        assert parsed["name"] == "http_requests_total"
        assert parsed["value"] == 42.0
        assert parsed["labels"] == {"method": "GET", "status": "200"}

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_metrics_endpoint_filters_by_since(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics?since=X filters samples by timestamp."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=100.0, value=1.0)
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=200.0, value=2.0)
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics?since=150")

        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["value"] == 2.0


class TestASGIMetricsPrometheusEndpoint:
    """Tests for the /metrics/prometheus endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_prometheus_endpoint_returns_200(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics/prometheus returns HTTP 200."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics/prometheus")

        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointContentType")
    @pytest.mark.asgi
    async def test_metrics_prometheus_has_correct_content_type(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics/prometheus returns correct Content-Type header."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
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
    ) -> None:
        """Test that /metrics/prometheus returns data in Prometheus format."""
        app = create_asgi_app(log_storage, metrics_storage_with_data)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics/prometheus")

        assert "http_requests_total" in response.text
        assert "42" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointCurrent")
    @pytest.mark.asgi
    async def test_metrics_prometheus_uses_encode_current(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics/prometheus keeps only latest sample per metric."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=100.0, value=1.0, labels={})
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=200.0, value=5.0, labels={})
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics/prometheus")

        lines = [line for line in response.text.strip().split("\n") if line]
        assert len(lines) == 1  # Only latest sample
        assert "5.0" in lines[0]

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.PrometheusEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_prometheus_empty_storage_returns_empty_body(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics/prometheus returns empty body when storage is empty."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.text == ""


class TestASGILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_logs_endpoint_returns_200(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs returns HTTP 200."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointContentType")
    @pytest.mark.asgi
    async def test_logs_endpoint_has_ndjson_content_type(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs returns correct Content-Type header."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointNDJSON")
    @pytest.mark.asgi
    async def test_logs_endpoint_returns_ndjson_format(
        self,
        log_storage_with_data: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
    ) -> None:
        """Test that /logs returns data in NDJSON format."""
        app = create_asgi_app(log_storage_with_data, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert "Test message" in response.text
        assert "INFO" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_filters_by_since(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs?since=X filters entries by timestamp."""
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

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_filters_by_level(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs?level=X filters entries by level."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="ERROR",
                message="Error message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?level=ERROR")

        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_level_filter_is_case_insensitive(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs?level=X is case-insensitive."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="ERROR",
                message="Error message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?level=error")

        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_combines_since_and_level(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs combines since and level filters."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="ERROR",
                message="Old error",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="ERROR",
                message="New error",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=300.0,
                level="INFO",
                message="New info",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?since=150&level=ERROR")

        assert "New error" in response.text
        assert "Old error" not in response.text
        assert "New info" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_level_returns_empty_for_nonexistent(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs treats invalid level as None (shows all)."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?level=FATAL")

        assert response.status_code == 200
        assert "Info message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_metrics_endpoint_handles_invalid_since_param(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics handles invalid since param gracefully."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=100.0, value=1.0)
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics?since=invalid")

        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["value"] == 1.0

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_handles_invalid_since_param(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs handles invalid since param gracefully."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Test message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?since=invalid")

        assert response.status_code == 200
        assert "Test message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_validates_level_whitelist(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs validates level parameter against whitelist."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="ERROR",
                message="Error message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs?level=INVALID_LEVEL")

        assert response.status_code == 200
        assert "Info message" in response.text
        assert "Error message" in response.text


class TestASGIErrorHandling:
    """Tests for error handling in endpoints."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_metrics_endpoint_handles_encoding_error_gracefully(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics handles encoding errors gracefully with 500."""
        app = create_asgi_app(log_storage, metrics_storage)

        # Mock the encode_ndjson to raise an exception
        import observabilipy.adapters.frameworks.asgi as asgi_module

        original_encode = asgi_module.encode_ndjson

        async def failing_encode(*args, **kwargs):
            raise ValueError("Encoding failed")

        asgi_module.encode_ndjson = failing_encode

        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/metrics")

            assert response.status_code == 500
            assert "error" in response.text.lower()
        finally:
            asgi_module.encode_ndjson = original_encode

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_logs_endpoint_handles_encoding_error_gracefully(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs handles encoding errors gracefully with 500."""
        app = create_asgi_app(log_storage, metrics_storage)

        # Mock the encode_logs to raise an exception
        import observabilipy.adapters.frameworks.asgi as asgi_module

        original_encode = asgi_module.encode_logs

        async def failing_encode(*args, **kwargs):
            raise ValueError("Encoding failed")

        asgi_module.encode_logs = failing_encode

        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/logs")

            assert response.status_code == 500
            assert "error" in response.text.lower()
        finally:
            asgi_module.encode_logs = original_encode


class TestASGIRouting:
    """Tests for routing and error handling."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.RoutingUnknownPath")
    @pytest.mark.asgi
    async def test_unknown_path_returns_404(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that unknown paths return HTTP 404."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/unknown")

        assert response.status_code == 404


class TestASGIEmptyStorage:
    """Tests for edge cases with empty storage."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_metrics_empty_storage_returns_empty_body(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /metrics returns empty body when storage is empty."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_logs_empty_storage_returns_empty_body(
        self, log_storage: InMemoryLogStorage, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Test that /logs returns empty body when storage is empty."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""
