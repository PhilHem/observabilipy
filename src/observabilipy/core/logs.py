"""Log helper function for creating LogEntry objects."""

import time

from observabilipy.core.models import LogEntry


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
