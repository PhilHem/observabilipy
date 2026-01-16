"""Integration tests for WSGI generic adapter."""

import asyncio
import json

import pytest

from observabilipy.core.models import LogEntry, MetricSample


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine in a new event loop (for sync test helpers)."""
    return asyncio.run(coro)


class TestWSGIMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsEndpointReturnsStatus")
    @pytest.mark.wsgi
    def test_metrics_endpoint_returns_200(self, wsgi_client_with_storage) -> None:
        """Test that /metrics returns HTTP 200."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/metrics")
        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsEndpointContentType")
    @pytest.mark.wsgi
    def test_metrics_endpoint_has_ndjson_content_type(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics returns correct Content-Type header."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/metrics")
        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsEndpointNDJSON")
    @pytest.mark.wsgi
    def test_metrics_endpoint_returns_ndjson_format(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics returns data in NDJSON format."""
        client, _log_storage, metrics_storage = wsgi_client_with_storage
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
        response = client.get("/metrics")
        parsed = json.loads(response.text.strip())
        assert parsed["name"] == "http_requests_total"
        assert parsed["value"] == 42.0
        assert parsed["labels"] == {"method": "GET", "status": "200"}

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsEndpointSinceFilter")
    @pytest.mark.wsgi
    def test_metrics_endpoint_filters_by_since(self, wsgi_client_with_storage) -> None:
        """Test that /metrics?since=X filters samples by timestamp."""
        client, _log_storage, metrics_storage = wsgi_client_with_storage
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
        response = client.get("/metrics?since=150")
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["value"] == 2.0


class TestWSGIMetricsPrometheusEndpoint:
    """Tests for the /metrics/prometheus endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.PrometheusEndpointReturnsStatus")
    @pytest.mark.wsgi
    def test_metrics_prometheus_endpoint_returns_200(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics/prometheus returns HTTP 200."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.PrometheusEndpointContentType")
    @pytest.mark.wsgi
    def test_metrics_prometheus_has_correct_content_type(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics/prometheus returns correct Content-Type header."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/metrics/prometheus")
        expected_content_type = "text/plain; version=0.0.4; charset=utf-8"
        assert response.headers["content-type"] == expected_content_type

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.PrometheusEndpointFormat")
    @pytest.mark.wsgi
    def test_metrics_prometheus_returns_prometheus_format(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics/prometheus returns data in Prometheus format."""
        client, _log_storage, metrics_storage = wsgi_client_with_storage
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
        response = client.get("/metrics/prometheus")
        assert "http_requests_total" in response.text
        assert "42" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.PrometheusEndpointLatestOnly")
    @pytest.mark.wsgi
    def test_metrics_prometheus_uses_encode_current(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics/prometheus keeps only latest sample per metric."""
        client, _log_storage, metrics_storage = wsgi_client_with_storage
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
        response = client.get("/metrics/prometheus")
        lines = [line for line in response.text.strip().split("\n") if line]
        assert len(lines) == 1  # Only latest sample
        assert "5.0" in lines[0]

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.PrometheusEndpointEmptyStorage")
    @pytest.mark.wsgi
    def test_metrics_prometheus_empty_storage_returns_empty_body(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics/prometheus returns empty body when storage is empty."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
        assert response.text == ""


class TestWSGILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointReturnsStatus")
    @pytest.mark.wsgi
    def test_logs_endpoint_returns_200(self, wsgi_client_with_storage) -> None:
        """Test that /logs returns HTTP 200."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/logs")
        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointContentType")
    @pytest.mark.wsgi
    def test_logs_endpoint_has_ndjson_content_type(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs returns correct Content-Type header."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/logs")
        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointNDJSON")
    @pytest.mark.wsgi
    def test_logs_endpoint_returns_ndjson_format(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs returns data in NDJSON format."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        response = client.get("/logs")
        assert "Test message" in response.text
        assert "INFO" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointSinceFilter")
    @pytest.mark.wsgi
    def test_logs_endpoint_filters_by_since(self, wsgi_client_with_storage) -> None:
        """Test that /logs?since=X filters entries by timestamp."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        response = client.get("/logs?since=150")
        assert "New message" in response.text
        assert "Old message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointLevelFilter")
    @pytest.mark.wsgi
    def test_logs_endpoint_filters_by_level(self, wsgi_client_with_storage) -> None:
        """Test that /logs?level=X filters entries by level."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        response = client.get("/logs?level=ERROR")
        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointLevelFilterCaseInsensitive")
    @pytest.mark.wsgi
    def test_logs_endpoint_level_filter_is_case_insensitive(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs?level=X is case-insensitive."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        response = client.get("/logs?level=error")
        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointCombinedFilters")
    @pytest.mark.wsgi
    def test_logs_endpoint_combines_since_and_level(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs combines since and level filters."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        response = client.get("/logs?since=150&level=ERROR")
        assert "New error" in response.text
        assert "Old error" not in response.text
        assert "New info" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEndpointInvalidLevel")
    @pytest.mark.wsgi
    def test_logs_endpoint_level_returns_empty_for_nonexistent(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs treats invalid level as None (shows all)."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        response = client.get("/logs?level=FATAL")
        assert response.status_code == 200
        assert "Info message" in response.text


class TestWSGIRouting:
    """Tests for routing and error handling."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.Routing404NotFound")
    @pytest.mark.wsgi
    def test_unknown_path_returns_404(self, wsgi_client_with_storage) -> None:
        """Test that unknown paths return HTTP 404."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/unknown")
        assert response.status_code == 404


class TestWSGIEmptyStorage:
    """Tests for edge cases with empty storage."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsEmptyStorage")
    @pytest.mark.wsgi
    def test_metrics_empty_storage_returns_empty_body(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics returns empty body when storage is empty."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsEmptyStorage")
    @pytest.mark.wsgi
    def test_logs_empty_storage_returns_empty_body(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs returns empty body when storage is empty."""
        client, _log_storage, _metrics_storage = wsgi_client_with_storage
        response = client.get("/logs")
        assert response.status_code == 200
        assert response.text == ""


class TestWSGIParameterValidation:
    """Tests for query parameter validation."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsInvalidSinceParam")
    @pytest.mark.wsgi
    def test_wsgi_metrics_handles_invalid_since_param(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics handles invalid since param gracefully."""
        client, _log_storage, metrics_storage = wsgi_client_with_storage
        _run_async(
            metrics_storage.write(
                MetricSample(name="counter", timestamp=100.0, value=1.0)
            )
        )
        response = client.get("/metrics?since=invalid")
        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["value"] == 1.0

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsInvalidSinceParam")
    @pytest.mark.wsgi
    def test_wsgi_logs_handles_invalid_since_param(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs handles invalid since param gracefully."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="INFO",
                    message="Test message",
                    attributes={},
                )
            )
        )
        response = client.get("/logs?since=invalid")
        assert response.status_code == 200
        assert "Test message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsInvalidLevelParam")
    @pytest.mark.wsgi
    def test_wsgi_logs_validates_level_against_whitelist(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs validates level parameter against whitelist."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
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
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=200.0,
                    level="ERROR",
                    message="Error message",
                    attributes={},
                )
            )
        )
        response = client.get("/logs?level=INVALID_LEVEL")
        assert response.status_code == 200
        assert "Info message" in response.text
        assert "Error message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.MetricsInvalidSinceParam")
    @pytest.mark.wsgi
    def test_wsgi_metrics_since_parameter_validation(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /metrics validates since parameter (negative, NaN, inf)."""
        client, _log_storage, metrics_storage = wsgi_client_with_storage
        _run_async(
            metrics_storage.write(
                MetricSample(name="counter", timestamp=100.0, value=1.0)
            )
        )
        # Test negative since value defaults to 0.0 (returns all)
        response = client.get("/metrics?since=-10")
        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["value"] == 1.0
        # Test NaN since value defaults to 0.0 (returns all)
        response = client.get("/metrics?since=nan")
        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["value"] == 1.0
        # Test inf since value defaults to 0.0 (returns all)
        response = client.get("/metrics?since=inf")
        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["value"] == 1.0

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.WSGI.LogsInvalidSinceParam")
    @pytest.mark.wsgi
    def test_wsgi_logs_since_parameter_validation(
        self, wsgi_client_with_storage
    ) -> None:
        """Test that /logs validates since parameter (negative, NaN, inf)."""
        client, log_storage, _metrics_storage = wsgi_client_with_storage
        _run_async(
            log_storage.write(
                LogEntry(
                    timestamp=100.0,
                    level="INFO",
                    message="Test message",
                    attributes={},
                )
            )
        )
        # Test negative since value defaults to 0.0 (returns all)
        response = client.get("/logs?since=-10")
        assert response.status_code == 200
        assert "Test message" in response.text
        # Test NaN since value defaults to 0.0 (returns all)
        response = client.get("/logs?since=nan")
        assert response.status_code == 200
        assert "Test message" in response.text
        # Test inf since value defaults to 0.0 (returns all)
        response = client.get("/logs?since=inf")
        assert response.status_code == 200
        assert "Test message" in response.text
