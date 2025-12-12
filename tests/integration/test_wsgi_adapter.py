"""Integration tests for WSGI generic adapter."""

import asyncio
import json

import httpx
import pytest

from observabilipy.adapters.frameworks.wsgi import create_wsgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine in a new event loop (for sync test helpers)."""
    return asyncio.run(coro)


class TestWSGIMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.wsgi
    def test_metrics_endpoint_returns_200(self) -> None:
        """Test that /metrics returns HTTP 200."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics")

        assert response.status_code == 200

    @pytest.mark.wsgi
    def test_metrics_endpoint_has_ndjson_content_type(self) -> None:
        """Test that /metrics returns correct Content-Type header."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.wsgi
    def test_metrics_endpoint_returns_ndjson_format(self) -> None:
        """Test that /metrics returns data in NDJSON format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            metrics_storage.write(
                MetricSample(
                    name="http_requests_total",
                    value=42.0,
                    timestamp=1000.0,
                    labels={"method": "GET", "status": "200"},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics")

        parsed = json.loads(response.text.strip())
        assert parsed["name"] == "http_requests_total"
        assert parsed["value"] == 42.0
        assert parsed["labels"] == {"method": "GET", "status": "200"}

    @pytest.mark.wsgi
    def test_metrics_endpoint_filters_by_since(self) -> None:
        """Test that /metrics?since=X filters samples by timestamp."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            metrics_storage.write(
                MetricSample(name="counter", timestamp=100.0, value=1.0)
            )
        )
        _run_async(
            metrics_storage.write(
                MetricSample(name="counter", timestamp=200.0, value=2.0)
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics?since=150")

        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["value"] == 2.0


class TestWSGIMetricsPrometheusEndpoint:
    """Tests for the /metrics/prometheus endpoint."""

    @pytest.mark.wsgi
    def test_metrics_prometheus_endpoint_returns_200(self) -> None:
        """Test that /metrics/prometheus returns HTTP 200."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics/prometheus")

        assert response.status_code == 200

    @pytest.mark.wsgi
    def test_metrics_prometheus_has_correct_content_type(self) -> None:
        """Test that /metrics/prometheus returns correct Content-Type header."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics/prometheus")

        expected_content_type = "text/plain; version=0.0.4; charset=utf-8"
        assert response.headers["content-type"] == expected_content_type

    @pytest.mark.wsgi
    def test_metrics_prometheus_returns_prometheus_format(self) -> None:
        """Test that /metrics/prometheus returns data in Prometheus format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            metrics_storage.write(
                MetricSample(
                    name="http_requests_total",
                    value=42.0,
                    timestamp=1000.0,
                    labels={"method": "GET", "status": "200"},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics/prometheus")

        assert "http_requests_total" in response.text
        assert "42" in response.text

    @pytest.mark.wsgi
    def test_metrics_prometheus_uses_encode_current(self) -> None:
        """Test that /metrics/prometheus keeps only latest sample per metric."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            metrics_storage.write(
                MetricSample(name="counter", timestamp=100.0, value=1.0, labels={})
            )
        )
        _run_async(
            metrics_storage.write(
                MetricSample(name="counter", timestamp=200.0, value=5.0, labels={})
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics/prometheus")

        lines = [line for line in response.text.strip().split("\n") if line]
        assert len(lines) == 1  # Only latest sample
        assert "5.0" in lines[0]

    @pytest.mark.wsgi
    def test_metrics_prometheus_empty_storage_returns_empty_body(self) -> None:
        """Test that /metrics/prometheus returns empty body when storage is empty."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.text == ""


class TestWSGILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.wsgi
    def test_logs_endpoint_returns_200(self) -> None:
        """Test that /logs returns HTTP 200."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs")

        assert response.status_code == 200

    @pytest.mark.wsgi
    def test_logs_endpoint_has_ndjson_content_type(self) -> None:
        """Test that /logs returns correct Content-Type header."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.wsgi
    def test_logs_endpoint_returns_ndjson_format(self) -> None:
        """Test that /logs returns data in NDJSON format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=1000.0,
                    level="INFO",
                    message="Test message",
                    attributes={"key": "value"},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs")

        assert "Test message" in response.text
        assert "INFO" in response.text

    @pytest.mark.wsgi
    def test_logs_endpoint_filters_by_since(self) -> None:
        """Test that /logs?since=X filters entries by timestamp."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="INFO",
                    message="Old message",
                    attributes={},
                )
            )
        )
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=200.0,
                    level="INFO",
                    message="New message",
                    attributes={},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs?since=150")

        assert "New message" in response.text
        assert "Old message" not in response.text

    @pytest.mark.wsgi
    def test_logs_endpoint_filters_by_level(self) -> None:
        """Test that /logs?level=X filters entries by level."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="ERROR",
                    message="Error message",
                    attributes={},
                )
            )
        )
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=200.0,
                    level="INFO",
                    message="Info message",
                    attributes={},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs?level=ERROR")

        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.wsgi
    def test_logs_endpoint_level_filter_is_case_insensitive(self) -> None:
        """Test that /logs?level=X is case-insensitive."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="ERROR",
                    message="Error message",
                    attributes={},
                )
            )
        )
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=200.0,
                    level="INFO",
                    message="Info message",
                    attributes={},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs?level=error")

        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.wsgi
    def test_logs_endpoint_combines_since_and_level(self) -> None:
        """Test that /logs combines since and level filters."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="ERROR",
                    message="Old error",
                    attributes={},
                )
            )
        )
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=200.0,
                    level="ERROR",
                    message="New error",
                    attributes={},
                )
            )
        )
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=300.0,
                    level="INFO",
                    message="New info",
                    attributes={},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs?since=150&level=ERROR")

        assert "New error" in response.text
        assert "Old error" not in response.text
        assert "New info" not in response.text

    @pytest.mark.wsgi
    def test_logs_endpoint_level_returns_empty_for_nonexistent(self) -> None:
        """Test that /logs returns empty for non-existent level."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="INFO",
                    message="Info message",
                    attributes={},
                )
            )
        )
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs?level=FATAL")

        assert response.status_code == 200
        assert response.text == ""


class TestWSGIRouting:
    """Tests for routing and error handling."""

    @pytest.mark.wsgi
    def test_unknown_path_returns_404(self) -> None:
        """Test that unknown paths return HTTP 404."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/unknown")

        assert response.status_code == 404


class TestWSGIEmptyStorage:
    """Tests for edge cases with empty storage."""

    @pytest.mark.wsgi
    def test_metrics_empty_storage_returns_empty_body(self) -> None:
        """Test that /metrics returns empty body when storage is empty."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.wsgi
    def test_logs_empty_storage_returns_empty_body(self) -> None:
        """Test that /logs returns empty body when storage is empty."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        app = create_wsgi_app(log_storage, metrics_storage)

        with httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        ) as client:
            response = client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""
