"""E2E tests for the complete log pipeline.

Tests the full flow: HTTP request → framework adapter → storage → encoding → response.
"""

import json

import httpx
import pytest

from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
)
from observabilipy.core.models import LogEntry


@pytest.mark.e2e
class TestLogWriteAndRead:
    """Test writing logs and reading them back via HTTP."""

    async def test_logs_written_appear_in_endpoint(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Logs written to storage appear in /logs endpoint."""
        await log_storage.write(
            LogEntry(
                timestamp=1000.0,
                level="INFO",
                message="Test message",
                attributes={"service": "test"},
            )
        )

        response = await client.get("/logs")

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["message"] == "Test message"
        assert entry["level"] == "INFO"
        assert entry["attributes"]["service"] == "test"

    async def test_multiple_logs_returned_in_order(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Multiple log entries are returned in timestamp order."""
        await log_storage.write(
            LogEntry(timestamp=300.0, level="ERROR", message="Third", attributes={})
        )
        await log_storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="First", attributes={})
        )
        await log_storage.write(
            LogEntry(timestamp=200.0, level="WARN", message="Second", attributes={})
        )

        response = await client.get("/logs")

        lines = response.text.strip().split("\n")
        assert len(lines) == 3
        messages = [json.loads(line)["message"] for line in lines]
        assert messages == ["First", "Second", "Third"]


@pytest.mark.e2e
class TestLogFiltering:
    """Test the since parameter for log filtering."""

    async def test_since_filters_old_entries(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """The since parameter excludes entries at or before the threshold."""
        await log_storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="old", attributes={})
        )
        await log_storage.write(
            LogEntry(timestamp=200.0, level="INFO", message="new", attributes={})
        )

        response = await client.get("/logs?since=100")

        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["message"] == "new"

    async def test_since_with_no_matches_returns_empty(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """When since is newer than all entries, returns empty response."""
        await log_storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="old", attributes={})
        )

        response = await client.get("/logs?since=200")

        assert response.status_code == 200
        assert response.text == ""


@pytest.mark.e2e
class TestLogNDJSONFormat:
    """Test that logs are correctly formatted as NDJSON."""

    async def test_content_type_is_ndjson(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Response has application/x-ndjson content type."""
        await log_storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="test", attributes={})
        )

        response = await client.get("/logs")

        assert response.headers["content-type"] == "application/x-ndjson"

    async def test_each_line_is_valid_json(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Each line in the response is valid JSON."""
        for i in range(5):
            await log_storage.write(
                LogEntry(
                    timestamp=float(i),
                    level="INFO",
                    message=f"Message {i}",
                    attributes={},
                )
            )

        response = await client.get("/logs")

        lines = response.text.strip().split("\n")
        for line in lines:
            entry = json.loads(line)  # Should not raise
            assert "timestamp" in entry
            assert "level" in entry
            assert "message" in entry
            assert "attributes" in entry

    async def test_response_ends_with_newline(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """NDJSON response ends with a trailing newline."""
        await log_storage.write(
            LogEntry(timestamp=100.0, level="INFO", message="test", attributes={})
        )

        response = await client.get("/logs")

        assert response.text.endswith("\n")

    async def test_attributes_serialized_correctly(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Complex attributes are serialized to JSON correctly."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="test",
                attributes={
                    "string": "value",
                    "number": 42,
                    "float": 3.14,
                    "bool": True,
                },
            )
        )

        response = await client.get("/logs")

        entry = json.loads(response.text.strip())
        assert entry["attributes"]["string"] == "value"
        assert entry["attributes"]["number"] == 42
        assert entry["attributes"]["float"] == 3.14
        assert entry["attributes"]["bool"] is True


@pytest.mark.e2e
class TestLogEdgeCases:
    """Test edge cases in the log pipeline."""

    async def test_empty_storage_returns_empty_response(
        self,
        client: httpx.AsyncClient,
    ) -> None:
        """Empty storage returns 200 with empty body."""
        response = await client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""

    async def test_special_characters_in_message(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Messages with special characters are encoded correctly."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message='Line1\nLine2\t"quoted"\\backslash',
                attributes={},
            )
        )

        response = await client.get("/logs")

        entry = json.loads(response.text.strip())
        assert entry["message"] == 'Line1\nLine2\t"quoted"\\backslash'

    async def test_unicode_in_message(
        self,
        log_storage: InMemoryLogStorage,
        client: httpx.AsyncClient,
    ) -> None:
        """Unicode characters are handled correctly."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Hello 世界 🌍 émojis",
                attributes={"key": "日本語"},
            )
        )

        response = await client.get("/logs")

        entry = json.loads(response.text.strip())
        assert entry["message"] == "Hello 世界 🌍 émojis"
        assert entry["attributes"]["key"] == "日本語"
