"""Python logging handler adapter for observabilipy.

This adapter bridges Python's standard library logging module to the
LogStoragePort, allowing logs to be captured and stored via observabilipy.
"""

import asyncio
import logging
import traceback

from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort

# Standard LogRecord attributes that should not be treated as extra fields
_STANDARD_LOGRECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


# Default attributes to extract from LogRecord
_DEFAULT_INCLUDE_ATTRS = ["module", "funcName", "lineno", "pathname"]


class ObservabilipyHandler(logging.Handler):
    """Logging handler that writes log records to a LogStoragePort.

    Example:
        ```python
        from observabilipy import ObservabilipyHandler, InMemoryLogStorage

        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)
        logging.getLogger().addHandler(handler)
        ```
    """

    def __init__(
        self,
        storage: LogStoragePort,
        include_attrs: list[str] | None = None,
    ) -> None:
        """Initialize the handler with a log storage backend.

        Args:
            storage: Storage adapter implementing LogStoragePort.
            include_attrs: List of LogRecord attributes to include. Defaults to
                ["module", "funcName", "lineno", "pathname"].
        """
        super().__init__()
        self._storage = storage
        self._include_attrs = include_attrs or _DEFAULT_INCLUDE_ATTRS

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the storage backend.

        Args:
            record: The log record to emit.
        """
        # Map of attribute names to their values from LogRecord
        attr_mapping: dict[str, str | int | float | bool] = {
            "module": record.name,
            "funcName": record.funcName or "",
            "lineno": record.lineno,
            "pathname": record.pathname,
        }

        # Build attributes based on include_attrs configuration
        attributes: dict[str, str | int | float | bool] = {
            key: attr_mapping[key] for key in self._include_attrs if key in attr_mapping
        }

        # Add any extra attributes passed via logging call
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOGRECORD_ATTRS and isinstance(
                value, (str, int, float, bool)
            ):
                attributes[key] = value

        # Extract exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type is not None:
                attributes["exc_type"] = exc_type.__name__
            if exc_value is not None:
                attributes["exc_message"] = str(exc_value)
            if exc_tb is not None:
                attributes["exc_traceback"] = "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                )

        entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            message=record.getMessage(),
            attributes=attributes,
        )
        asyncio.run(self._storage.write(entry))
