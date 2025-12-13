"""Tests for log helper functions."""

import time

import pytest

from observabilipy.core.logs import debug, error, info, log, warn
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


class TestInfoHelper:
    """Tests for info() helper function."""

    @pytest.mark.core
    def test_info_creates_log_entry_with_info_level(self) -> None:
        """Info creates a LogEntry with INFO level."""
        entry = info("Server started")
        assert entry.level == "INFO"
        assert entry.message == "Server started"

    @pytest.mark.core
    def test_info_accepts_attributes(self) -> None:
        """Info accepts attributes as keyword arguments."""
        entry = info("Request completed", request_id="abc")
        assert entry.attributes == {"request_id": "abc"}


class TestErrorHelper:
    """Tests for error() helper function."""

    @pytest.mark.core
    def test_error_creates_log_entry_with_error_level(self) -> None:
        """Error creates a LogEntry with ERROR level."""
        entry = error("Connection failed")
        assert entry.level == "ERROR"
        assert entry.message == "Connection failed"

    @pytest.mark.core
    def test_error_accepts_attributes(self) -> None:
        """Error accepts attributes as keyword arguments."""
        entry = error("Timeout", retry_count=3)
        assert entry.attributes == {"retry_count": 3}


class TestDebugHelper:
    """Tests for debug() helper function."""

    @pytest.mark.core
    def test_debug_creates_log_entry_with_debug_level(self) -> None:
        """Debug creates a LogEntry with DEBUG level."""
        entry = debug("Entering function")
        assert entry.level == "DEBUG"
        assert entry.message == "Entering function"

    @pytest.mark.core
    def test_debug_accepts_attributes(self) -> None:
        """Debug accepts attributes as keyword arguments."""
        entry = debug("Variable state", x=42)
        assert entry.attributes == {"x": 42}


class TestWarnHelper:
    """Tests for warn() helper function."""

    @pytest.mark.core
    def test_warn_creates_log_entry_with_warn_level(self) -> None:
        """Warn creates a LogEntry with WARN level."""
        entry = warn("Deprecated API used")
        assert entry.level == "WARN"
        assert entry.message == "Deprecated API used"

    @pytest.mark.core
    def test_warn_accepts_attributes(self) -> None:
        """Warn accepts attributes as keyword arguments."""
        entry = warn("High memory", usage_pct=85.5)
        assert entry.attributes == {"usage_pct": 85.5}


class TestPackageExports:
    """Tests for package-level exports."""

    @pytest.mark.core
    def test_log_importable_from_package(self) -> None:
        """Log helper is importable from observabilipy package."""
        from observabilipy import log

        assert callable(log)

    @pytest.mark.core
    def test_level_helpers_importable_from_package(self) -> None:
        """Level-specific log helpers are importable from observabilipy package."""
        from observabilipy import debug, error, info, warn

        assert all(callable(fn) for fn in [info, error, debug, warn])
