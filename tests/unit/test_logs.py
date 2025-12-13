"""Tests for log helper functions."""

import time

import pytest

from observabilipy.core.logs import (
    TimedLogResult,
    debug,
    error,
    info,
    log,
    log_exception,
    timed_log,
    warn,
)
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


class TestTimedLogResult:
    """Tests for TimedLogResult class."""

    @pytest.mark.core
    def test_timed_log_result_has_logs_list(self) -> None:
        """TimedLogResult has an empty logs list by default."""
        result = TimedLogResult()
        assert result.logs == []


class TestTimedLog:
    """Tests for timed_log() context manager."""

    @pytest.mark.core
    def test_timed_log_yields_result(self) -> None:
        """timed_log yields a TimedLogResult."""
        with timed_log("test operation") as result:
            assert isinstance(result, TimedLogResult)

    @pytest.mark.core
    def test_timed_log_creates_entry_log(self) -> None:
        """timed_log creates entry log with [entry] suffix."""
        with timed_log("processing order") as result:
            pass
        assert len(result.logs) >= 1
        entry = result.logs[0]
        assert entry.message == "processing order [entry]"
        assert entry.attributes.get("phase") == "entry"

    @pytest.mark.core
    def test_timed_log_creates_exit_log_with_elapsed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """timed_log creates exit log with elapsed time."""
        times = iter([100.0, 100.5])  # 0.5 second elapsed
        monkeypatch.setattr(time, "perf_counter", lambda: next(times))

        with timed_log("task") as result:
            pass

        assert len(result.logs) == 2
        exit_log = result.logs[1]
        assert exit_log.message == "task [exit]"
        assert exit_log.attributes["phase"] == "exit"
        assert exit_log.attributes["elapsed_seconds"] == 0.5

    @pytest.mark.core
    def test_timed_log_with_custom_level(self) -> None:
        """timed_log accepts custom log level."""
        with timed_log("debug task", level="DEBUG") as result:
            pass
        assert result.logs[0].level == "DEBUG"
        assert result.logs[1].level == "DEBUG"

    @pytest.mark.core
    def test_timed_log_with_attributes(self) -> None:
        """timed_log passes attributes to both entry and exit logs."""
        with timed_log("order", order_id=123, customer="alice") as result:
            pass
        # Entry log has custom attributes
        assert result.logs[0].attributes["order_id"] == 123
        assert result.logs[0].attributes["customer"] == "alice"
        assert result.logs[0].attributes["phase"] == "entry"
        # Exit log also has them
        assert result.logs[1].attributes["order_id"] == 123
        assert result.logs[1].attributes["customer"] == "alice"
        assert result.logs[1].attributes["phase"] == "exit"


class TestLogExceptionHelper:
    """Tests for log_exception() helper function."""

    @pytest.mark.core
    def test_log_exception_creates_error_level_entry(self) -> None:
        """log_exception creates a LogEntry with ERROR level."""
        try:
            raise ValueError("test error")
        except ValueError:
            entry = log_exception()
        assert entry.level == "ERROR"

    @pytest.mark.core
    def test_log_exception_uses_exception_message_as_default_message(self) -> None:
        """log_exception uses the exception message as the default log message."""
        try:
            raise ValueError("something went wrong")
        except ValueError:
            entry = log_exception()
        assert entry.message == "something went wrong"

    @pytest.mark.core
    def test_log_exception_allows_custom_message(self) -> None:
        """log_exception allows overriding the message."""
        try:
            raise ValueError("original")
        except ValueError:
            entry = log_exception("Custom message")
        assert entry.message == "Custom message"

    @pytest.mark.core
    def test_log_exception_captures_exception_type(self) -> None:
        """log_exception captures the exception type name."""
        try:
            raise KeyError("missing key")
        except KeyError:
            entry = log_exception()
        assert entry.attributes["exception_type"] == "KeyError"

    @pytest.mark.core
    def test_log_exception_captures_exception_message(self) -> None:
        """log_exception captures the exception message in attributes."""
        try:
            raise RuntimeError("detailed error info")
        except RuntimeError:
            entry = log_exception()
        assert entry.attributes["exception_message"] == "detailed error info"

    @pytest.mark.core
    def test_log_exception_captures_traceback(self) -> None:
        """log_exception captures the formatted traceback."""
        try:
            raise TypeError("type mismatch")
        except TypeError:
            entry = log_exception()
        assert "traceback" in entry.attributes
        assert "TypeError" in entry.attributes["traceback"]
        assert "type mismatch" in entry.attributes["traceback"]

    @pytest.mark.core
    def test_log_exception_accepts_additional_attributes(self) -> None:
        """log_exception accepts additional attributes as kwargs."""
        try:
            raise ValueError("error")
        except ValueError:
            entry = log_exception(request_id="abc123", user_id=42)
        assert entry.attributes["request_id"] == "abc123"
        assert entry.attributes["user_id"] == 42

    @pytest.mark.core
    def test_log_exception_auto_captures_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """log_exception automatically captures current timestamp."""
        monkeypatch.setattr(time, "time", lambda: 1702300000.0)
        try:
            raise ValueError("error")
        except ValueError:
            entry = log_exception()
        assert entry.timestamp == 1702300000.0

    @pytest.mark.core
    def test_log_exception_returns_log_entry(self) -> None:
        """log_exception returns a LogEntry instance."""
        try:
            raise ValueError("error")
        except ValueError:
            entry = log_exception()
        assert isinstance(entry, LogEntry)


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

    @pytest.mark.core
    def test_timed_log_importable_from_package(self) -> None:
        """timed_log and TimedLogResult are importable from observabilipy package."""
        from observabilipy import TimedLogResult, timed_log

        assert callable(timed_log)
        assert TimedLogResult is not None

    @pytest.mark.core
    def test_log_exception_importable_from_package(self) -> None:
        """log_exception is importable from observabilipy package."""
        from observabilipy import log_exception

        assert callable(log_exception)
