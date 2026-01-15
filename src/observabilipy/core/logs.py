"""Log helper function for creating LogEntry objects."""

import sys
import time
import traceback
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

from observabilipy.core.models import LogEntry


@dataclass
class StructuredLogger:
    """Fluent logger for structured logging with fields."""

    _module_name: str
    _fields: dict[str, str | int | float | bool] = field(default_factory=dict)

    def with_fields(self, **fields: str | int | float | bool) -> "StructuredLogger":
        """Add structured fields to the next log call.

        Args:
            **fields: Field names and values

        Returns:
            New logger instance with fields set
        """
        return StructuredLogger(
            _module_name=self._module_name,
            _fields={**self._fields, **fields},
        )

    def info(self, message: str) -> LogEntry:
        """Log an INFO message with accumulated fields."""
        return info(message, **self._fields)

    def debug(self, message: str) -> LogEntry:
        """Log a DEBUG message with accumulated fields."""
        return debug(message, **self._fields)

    def error(self, message: str) -> LogEntry:
        """Log an ERROR message with accumulated fields."""
        return error(message, **self._fields)

    def warn(self, message: str) -> LogEntry:
        """Log a WARN message with accumulated fields."""
        return warn(message, **self._fields)

    def exception(self, message: str | None = None) -> LogEntry:
        """Log an exception with accumulated fields.

        Must be called from within an exception handler (except block).
        """
        return log_exception(message, **self._fields)


@dataclass
class TimedLogResult:
    """Result object for timed_log context manager."""

    logs: list[LogEntry] = field(default_factory=list)


@contextmanager
def timed_log(
    message: str,
    level: str = "INFO",
    **attributes: str | int | float | bool,
) -> Generator[TimedLogResult]:
    """Context manager that logs entry and exit with elapsed time.

    Args:
        message: The base log message
        level: Log level (default "INFO")
        **attributes: Additional structured fields

    Yields:
        TimedLogResult containing entry and exit LogEntry objects

    Example:
        >>> with timed_log("Processing order", order_id=123) as result:
        ...     pass  # do work here
        >>> len(result.logs)
        2
        >>> result.logs[0].message
        'Processing order [entry]'
        >>> "elapsed_seconds" in result.logs[1].attributes
        True
    """
    result = TimedLogResult()
    start = time.perf_counter()
    entry_log = LogEntry(
        timestamp=time.time(),
        level=level,
        message=f"{message} [entry]",
        attributes={"phase": "entry", **attributes},
    )
    result.logs.append(entry_log)
    yield result
    elapsed = time.perf_counter() - start
    exit_log = LogEntry(
        timestamp=time.time(),
        level=level,
        message=f"{message} [exit]",
        attributes={"phase": "exit", "elapsed_seconds": elapsed, **attributes},
    )
    result.logs.append(exit_log)


def log(
    level: str,
    message: str,
    **attributes: str | int | float | bool,
) -> LogEntry:
    """Create a log entry with automatic timestamp.

    Args:
        level: Log level (e.g., "INFO", "ERROR", "DEBUG")
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with current timestamp

    Example:
        >>> entry = log("INFO", "User logged in", user_id=123)
        >>> entry.level
        'INFO'
        >>> entry.message
        'User logged in'
        >>> entry.attributes["user_id"]
        123
    """
    return LogEntry(
        timestamp=time.time(),
        level=level,
        message=message,
        attributes=dict(attributes),
    )


def info(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create an INFO log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with INFO level and current timestamp

    Example:
        >>> entry = info("Server started", port=8080)
        >>> entry.level
        'INFO'
        >>> entry.attributes["port"]
        8080
    """
    return log("INFO", message, **attributes)


def error(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create an ERROR log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with ERROR level and current timestamp

    Example:
        >>> entry = error("Connection failed", host="db.example.com")
        >>> entry.level
        'ERROR'
    """
    return log("ERROR", message, **attributes)


def debug(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create a DEBUG log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with DEBUG level and current timestamp

    Example:
        >>> entry = debug("Cache hit", key="user:123")
        >>> entry.level
        'DEBUG'
    """
    return log("DEBUG", message, **attributes)


def warn(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create a WARN log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with WARN level and current timestamp

    Example:
        >>> entry = warn("Disk usage high", percent=85)
        >>> entry.level
        'WARN'
    """
    return log("WARN", message, **attributes)


def log_exception(
    message: str | None = None,
    **attributes: str | int | float | bool,
) -> LogEntry:
    """Create an ERROR log entry capturing current exception info.

    Must be called from within an exception handler (except block).

    Args:
        message: Optional custom message (defaults to exception message)
        **attributes: Additional structured fields

    Returns:
        LogEntry with ERROR level, exception details, and traceback

    Example:
        >>> try:
        ...     raise ValueError("Something went wrong")
        ... except ValueError:
        ...     entry = log_exception(request_id="abc123")
        >>> entry.level
        'ERROR'
        >>> entry.attributes["exception_type"]
        'ValueError'
        >>> "request_id" in entry.attributes
        True
    """
    exc_type, exc_value, _ = sys.exc_info()

    exc_type_name = exc_type.__name__ if exc_type else "Unknown"
    exc_message = str(exc_value) if exc_value else ""
    tb = traceback.format_exc()

    return LogEntry(
        timestamp=time.time(),
        level="ERROR",
        message=message if message is not None else exc_message,
        attributes={
            "exception_type": exc_type_name,
            "exception_message": exc_message,
            "traceback": tb,
            **attributes,
        },
    )


def get_logger(module_name: str) -> StructuredLogger:
    """Create a structured logger for a module.

    Args:
        module_name: Name of the module (typically __name__)

    Returns:
        StructuredLogger instance for fluent logging with fields

    Example:
        >>> logger = get_logger("my_module")
        >>> entry = logger.with_fields(user_id=123).info("User logged in")
        >>> entry.level
        'INFO'
        >>> entry.attributes['user_id']
        123
    """
    return StructuredLogger(_module_name=module_name)
