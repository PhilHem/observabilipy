"""Tests for NDJSON log encoder."""

import json
from collections.abc import AsyncIterator

import pytest

from observabilipy.core.encoding.ndjson import encode_logs
from observabilipy.core.models import LogEntry


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
