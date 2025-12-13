"""Log helper function for creating LogEntry objects."""

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

from observabilipy.core.models import LogEntry


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
    """
    return log("INFO", message, **attributes)


def error(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create an ERROR log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with ERROR level and current timestamp
    """
    return log("ERROR", message, **attributes)


def debug(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create a DEBUG log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with DEBUG level and current timestamp
    """
    return log("DEBUG", message, **attributes)


def warn(message: str, **attributes: str | int | float | bool) -> LogEntry:
    """Create a WARN log entry with automatic timestamp.

    Args:
        message: The log message
        **attributes: Additional structured fields

    Returns:
        LogEntry with WARN level and current timestamp
    """
    return log("WARN", message, **attributes)
