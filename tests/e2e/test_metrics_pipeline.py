"""E2E tests for the complete metrics pipeline.

Tests the full flow: HTTP request → framework adapter → storage → encoding → response.
"""

import httpx
import pytest

from observabilipy.adapters.storage.in_memory import InMemoryMetricsStorage
from observabilipy.core.models import MetricSample


@pytest.mark.e2e
class TestMetricsWriteAndScrape:
    """Test writing metrics and scraping them via HTTP."""

    async def test_metrics_written_appear_in_endpoint(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Metrics written to storage appear in /metrics endpoint."""
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1000.0,
                value=42.0,
                labels={"method": "GET", "status": "200"},
            )
        )

        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "http_requests_total" in response.text
        assert "42" in response.text

    async def test_multiple_metrics_all_returned(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Multiple metric samples are all returned."""
        await metrics_storage.write(
            MetricSample(
                name="requests_total",
                timestamp=1000.0,
                value=100.0,
                labels={"path": "/api"},
            )
        )
        await metrics_storage.write(
            MetricSample(
                name="errors_total",
                timestamp=1000.0,
                value=5.0,
                labels={"path": "/api"},
            )
        )

        response = await client.get("/metrics")

        assert "requests_total" in response.text
        assert "errors_total" in response.text
        assert "100" in response.text
        assert "5" in response.text


@pytest.mark.e2e
class TestMetricsPrometheusFormat:
    """Test that metrics are correctly formatted in Prometheus exposition format."""

    async def test_content_type_is_prometheus(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Response has correct Prometheus content type."""
        await metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1000.0,
                value=1.0,
                labels={},
            )
        )

        response = await client.get("/metrics/prometheus")

        expected = "text/plain; version=0.0.4; charset=utf-8"
        assert response.headers["content-type"] == expected

    async def test_metric_format_with_labels(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Metrics with labels are formatted correctly."""
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "status": "200"},
            )
        )

        response = await client.get("/metrics/prometheus")

        # Should contain metric name with labels in alphabetical order
        assert "http_requests_total{" in response.text
        # Labels should be present
        assert 'method="GET"' in response.text
        assert 'status="200"' in response.text
        # Value should be present
        assert "42" in response.text

    async def test_metric_format_without_labels(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Metrics without labels are formatted correctly."""
        await metrics_storage.write(
            MetricSample(
                name="process_uptime_seconds",
                timestamp=1000.0,
                value=3600.0,
                labels={},
            )
        )

        response = await client.get("/metrics/prometheus")

        # Metric without labels has no braces
        lines = response.text.strip().split("\n")
        uptime_lines = [line for line in lines if "process_uptime_seconds" in line]
        assert len(uptime_lines) == 1
        # Should be: metric_name value timestamp
        assert "process_uptime_seconds" in uptime_lines[0]
        assert "3600" in uptime_lines[0]

    async def test_timestamp_in_milliseconds(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Timestamp is converted to milliseconds in output."""
        await metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1702300000.0,  # seconds
                value=1.0,
                labels={},
            )
        )

        response = await client.get("/metrics/prometheus")

        # 1702300000 seconds = 1702300000000 milliseconds
        assert "1702300000000" in response.text

    async def test_each_metric_on_separate_line(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Each metric sample is on its own line."""
        for i in range(3):
            await metrics_storage.write(
                MetricSample(
                    name=f"metric_{i}",
                    timestamp=1000.0 + i,
                    value=float(i),
                    labels={},
                )
            )

        response = await client.get("/metrics/prometheus")

        lines = [line for line in response.text.strip().split("\n") if line]
        assert len(lines) == 3


@pytest.mark.e2e
class TestMetricsLabelEscaping:
    """Test that label values are properly escaped in Prometheus format."""

    async def test_quotes_in_label_value_escaped(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Double quotes in label values are escaped."""
        await metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1000.0,
                value=1.0,
                labels={"path": '/api/"test"'},
            )
        )

        response = await client.get("/metrics/prometheus")

        # Quotes should be escaped as \"
        assert r"\"test\"" in response.text

    async def test_backslash_in_label_value_escaped(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Backslashes in label values are escaped."""
        await metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1000.0,
                value=1.0,
                labels={"path": "C:\\Users\\test"},
            )
        )

        response = await client.get("/metrics/prometheus")

        # Backslashes should be escaped as \\
        assert r"C:\\Users\\test" in response.text

    async def test_newline_in_label_value_escaped(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Newlines in label values are escaped."""
        await metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1000.0,
                value=1.0,
                labels={"desc": "line1\nline2"},
            )
        )

        response = await client.get("/metrics/prometheus")

        # Newline should be escaped as \n
        assert r"\n" in response.text


@pytest.mark.e2e
class TestMetricsEdgeCases:
    """Test edge cases in the metrics pipeline."""

    async def test_empty_storage_returns_empty_response(
        self,
        client: httpx.AsyncClient,
    ) -> None:
        """Empty storage returns 200 with empty body."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""

    async def test_float_precision_preserved(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Float values maintain precision."""
        await metrics_storage.write(
            MetricSample(
                name="precise_metric",
                timestamp=1000.0,
                value=3.141592653589793,
                labels={},
            )
        )

        response = await client.get("/metrics")

        assert "3.14159" in response.text

    async def test_zero_value_metric(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Zero-valued metrics are included in output."""
        await metrics_storage.write(
            MetricSample(
                name="zero_metric",
                timestamp=1000.0,
                value=0.0,
                labels={},
            )
        )

        response = await client.get("/metrics")

        assert "zero_metric" in response.text

    async def test_labels_sorted_alphabetically(
        self,
        metrics_storage: InMemoryMetricsStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Labels are sorted alphabetically in Prometheus output."""
        await metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1000.0,
                value=1.0,
                labels={"zebra": "z", "alpha": "a", "middle": "m"},
            )
        )

        response = await client.get("/metrics/prometheus")

        # Find the labels section
        line = response.text.strip()
        # Alpha should come before middle, which should come before zebra
        alpha_pos = line.find("alpha")
        middle_pos = line.find("middle")
        zebra_pos = line.find("zebra")
        assert alpha_pos < middle_pos < zebra_pos
