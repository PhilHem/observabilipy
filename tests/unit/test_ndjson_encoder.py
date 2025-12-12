"""Tests for NDJSON log encoder."""

import json
from collections.abc import AsyncIterator

import pytest

from observabilipy.core.encoding.ndjson import (
    encode_logs,
    encode_ndjson,
    encode_ndjson_sync,
)
from observabilipy.core.models import LogEntry, MetricSample


async def to_async_iter[T](items: list[T]) -> AsyncIterator[T]:
    """Convert a list to an async iterator for testing."""
    for item in items:
        yield item


class TestNdjsonEncoder:
    """Tests for NDJSON encoding of log entries."""

    @pytest.mark.encoding
    async def test_encode_single_entry(self) -> None:
        """Single LogEntry encodes to one JSON line."""
        entry = LogEntry(
            timestamp=1702300000.0,
            level="INFO",
            message="Application started",
        )

        result = await encode_logs(to_async_iter([entry]))

        parsed = json.loads(result.strip())
        assert parsed["timestamp"] == 1702300000.0
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Application started"
        assert parsed["attributes"] == {}

    @pytest.mark.encoding
    async def test_encode_multiple_entries(self) -> None:
        """Multiple entries are newline-delimited."""
        entries = [
            LogEntry(timestamp=1702300000.0, level="INFO", message="First"),
            LogEntry(timestamp=1702300001.0, level="ERROR", message="Second"),
        ]

        result = await encode_logs(to_async_iter(entries))

        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["message"] == "First"
        assert json.loads(lines[1])["message"] == "Second"

    @pytest.mark.encoding
    async def test_encode_empty_iterable(self) -> None:
        """Empty input returns empty string."""
        result = await encode_logs(to_async_iter([]))

        assert result == ""

    @pytest.mark.encoding
    async def test_encode_entry_with_attributes(self) -> None:
        """Attributes are serialized correctly."""
        entry = LogEntry(
            timestamp=1702300000.0,
            level="ERROR",
            message="Connection failed",
            attributes={"host": "localhost", "port": 5432, "retries": 3},
        )

        result = await encode_logs(to_async_iter([entry]))

        parsed = json.loads(result.strip())
        assert parsed["attributes"]["host"] == "localhost"
        assert parsed["attributes"]["port"] == 5432
        assert parsed["attributes"]["retries"] == 3

    @pytest.mark.encoding
    async def test_output_ends_with_newline(self) -> None:
        """Each entry ends with a newline character."""
        entry = LogEntry(
            timestamp=1702300000.0,
            level="INFO",
            message="Test",
        )

        result = await encode_logs(to_async_iter([entry]))

        assert result.endswith("\n")


class TestNdjsonMetricEncoder:
    """Tests for NDJSON encoding of metric samples."""

    @pytest.mark.encoding
    async def test_encode_metric_sample_single(self) -> None:
        """Single MetricSample encodes to one JSON line."""
        sample = MetricSample(
            name="http_requests_total",
            timestamp=1700000000.0,
            value=42.0,
        )

        result = await encode_ndjson(to_async_iter([sample]))

        obj = json.loads(result.strip())
        assert obj == {
            "name": "http_requests_total",
            "timestamp": 1700000000.0,
            "value": 42.0,
            "labels": {},
        }

    @pytest.mark.encoding
    async def test_encode_metric_sample_with_labels(self) -> None:
        """MetricSample labels are serialized correctly."""
        sample = MetricSample(
            name="http_requests_total",
            timestamp=1700000000.0,
            value=42.0,
            labels={"method": "GET", "status": "200"},
        )

        result = await encode_ndjson(to_async_iter([sample]))

        obj = json.loads(result.strip())
        assert obj["labels"] == {"method": "GET", "status": "200"}

    @pytest.mark.encoding
    async def test_encode_metric_sample_multiple(self) -> None:
        """Multiple samples are newline-delimited."""
        samples = [
            MetricSample(name="requests", timestamp=1.0, value=10.0),
            MetricSample(name="errors", timestamp=2.0, value=1.0),
        ]

        result = await encode_ndjson(to_async_iter(samples))

        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["name"] == "requests"
        assert json.loads(lines[1])["name"] == "errors"

    @pytest.mark.encoding
    async def test_encode_metric_sample_empty(self) -> None:
        """Empty iterable returns empty string."""
        result = await encode_ndjson(to_async_iter([]))

        assert result == ""

    @pytest.mark.encoding
    async def test_encode_metric_sample_ends_with_newline(self) -> None:
        """Output ends with a newline character."""
        sample = MetricSample(name="test", timestamp=1.0, value=1.0)

        result = await encode_ndjson(to_async_iter([sample]))

        assert result.endswith("\n")

    @pytest.mark.encoding
    def test_encode_metric_sample_sync(self) -> None:
        """Sync version works with regular iterables."""
        sample = MetricSample(name="gauge", timestamp=1.0, value=5.5)

        result = encode_ndjson_sync([sample])

        obj = json.loads(result.strip())
        assert obj["name"] == "gauge"
        assert obj["value"] == 5.5

    @pytest.mark.encoding
    def test_encode_metric_sample_sync_empty(self) -> None:
        """Sync version returns empty string for empty input."""
        result = encode_ndjson_sync([])

        assert result == ""
