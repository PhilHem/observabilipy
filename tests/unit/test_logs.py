"""Tests for log helper function."""

import time

import pytest

from observabilipy.core.logs import log
from observabilipy.core.models import LogEntry


class TestLog:
    """Tests for log() helper function."""

    @pytest.mark.core
    def test_log_creates_log_entry_with_level_and_message(self) -> None:
        """Log creates a LogEntry with the given level and message."""
        entry = log("INFO", "Server started")
        assert entry.level == "INFO"
        assert entry.message == "Server started"

    @pytest.mark.core
    def test_log_returns_log_entry_type(self) -> None:
        """Log returns a LogEntry instance."""
        entry = log("INFO", "Test message")
        assert isinstance(entry, LogEntry)

    @pytest.mark.core
    def test_log_auto_captures_timestamp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Log automatically captures current timestamp."""
        monkeypatch.setattr(time, "time", lambda: 1702300000.0)
        entry = log("INFO", "Test message")
        assert entry.timestamp == 1702300000.0

    @pytest.mark.core
    def test_log_accepts_attributes_as_kwargs(self) -> None:
        """Log accepts attributes as keyword arguments."""
        entry = log("ERROR", "Request failed", request_id="abc123", status=500)
        assert entry.attributes == {"request_id": "abc123", "status": 500}

    @pytest.mark.core
    def test_log_defaults_to_empty_attributes(self) -> None:
        """Log defaults to empty attributes dict."""
        entry = log("DEBUG", "Debug message")
        assert entry.attributes == {}

    @pytest.mark.core
    def test_log_preserves_attribute_types(self) -> None:
        """Log preserves attribute value types (str, int, float, bool)."""
        entry = log(
            "INFO",
            "Mixed types",
            name="test",
            count=42,
            ratio=3.14,
            enabled=True,
        )
        assert entry.attributes["name"] == "test"
        assert entry.attributes["count"] == 42
        assert entry.attributes["ratio"] == 3.14
        assert entry.attributes["enabled"] is True


class TestPackageExports:
    """Tests for package-level exports."""

    @pytest.mark.core
    def test_log_importable_from_package(self) -> None:
        """Log helper is importable from observabilipy package."""
        from observabilipy import log

        assert callable(log)
