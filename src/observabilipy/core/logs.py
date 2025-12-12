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
