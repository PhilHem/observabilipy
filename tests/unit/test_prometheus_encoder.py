"""Tests for Prometheus text format encoder."""

from collections.abc import AsyncIterator

import pytest

from observability.core.encoding.prometheus import encode_metrics
from observability.core.models import MetricSample


async def to_async_iter[T](items: list[T]) -> AsyncIterator[T]:
    """Convert a list to an async iterator for testing."""
    for item in items:
        yield item


class TestPrometheusEncoder:
    """Tests for Prometheus text format encoding of metric samples."""

    @pytest.mark.encoding
    async def test_encode_single_metric_no_labels(self) -> None:
        """Single MetricSample encodes to Prometheus format."""
        sample = MetricSample(
            name="requests_total",
            timestamp=1702300000.0,
            value=42.0,
        )

        result = await encode_metrics(to_async_iter([sample]))

        assert result == "requests_total 42.0 1702300000000\n"

    @pytest.mark.encoding
    async def test_encode_metric_with_labels(self) -> None:
        """Labels are formatted correctly."""
        sample = MetricSample(
            name="http_requests",
            timestamp=1702300000.0,
            value=1.0,
            labels={"method": "GET", "status": "200"},
        )

        result = await encode_metrics(to_async_iter([sample]))

        # Labels should be in sorted order for deterministic output
        assert result == 'http_requests{method="GET",status="200"} 1.0 1702300000000\n'

    @pytest.mark.encoding
    async def test_encode_multiple_metrics(self) -> None:
        """Multiple samples are newline-delimited."""
        samples = [
            MetricSample(name="metric_a", timestamp=1702300000.0, value=1.0),
            MetricSample(name="metric_b", timestamp=1702300001.0, value=2.0),
        ]

        result = await encode_metrics(to_async_iter(samples))

        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "metric_a 1.0 1702300000000"
        assert lines[1] == "metric_b 2.0 1702300001000"

    @pytest.mark.encoding
    async def test_encode_empty_iterable(self) -> None:
        """Empty input returns empty string."""
        result = await encode_metrics(to_async_iter([]))

        assert result == ""

    @pytest.mark.encoding
    async def test_output_ends_with_newline(self) -> None:
        """Output ends with newline character."""
        sample = MetricSample(
            name="test_metric",
            timestamp=1702300000.0,
            value=1.0,
        )

        result = await encode_metrics(to_async_iter([sample]))

        assert result.endswith("\n")

    @pytest.mark.encoding
    async def test_label_value_escaping(self) -> None:
        """Special characters in label values are escaped."""
        sample = MetricSample(
            name="test_metric",
            timestamp=1702300000.0,
            value=1.0,
            labels={
                "path": '/api/"test"',
                "note": "line1\nline2",
                "escape": "back\\slash",
            },
        )

        result = await encode_metrics(to_async_iter([sample]))

        # Prometheus escaping: \ -> \\, " -> \", newline -> \n
        assert r'escape="back\\slash"' in result
        assert r'note="line1\nline2"' in result
        assert r'path="/api/\"test\""' in result

    @pytest.mark.encoding
    async def test_float_value_precision(self) -> None:
        """Float values maintain precision."""
        sample = MetricSample(
            name="precise_metric",
            timestamp=1702300000.0,
            value=0.123456789,
        )

        result = await encode_metrics(to_async_iter([sample]))

        assert "0.123456789" in result
