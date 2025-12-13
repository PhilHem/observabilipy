"""Python logging handler adapter for observabilipy.

This adapter bridges Python's standard library logging module to the
LogStoragePort, allowing logs to be captured and stored via observabilipy.
"""

import asyncio
import logging
import queue
import threading
import traceback
from collections.abc import Callable

from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort

# Type alias for context provider callable
ContextProvider = Callable[[], dict[str, str | int | float | bool]]

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
        context_provider: ContextProvider | None = None,
        background_writer: bool = False,
    ) -> None:
        """Initialize the handler with a log storage backend.

        Args:
            storage: Storage adapter implementing LogStoragePort.
            include_attrs: List of LogRecord attributes to include. Defaults to
                ["module", "funcName", "lineno", "pathname"].
            context_provider: Optional callable that returns a dict of context
                attributes to include in every log entry. Useful for adding
                request IDs, user IDs, or other request-scoped context.
            background_writer: If True, writes are queued and processed by a
                background thread. This guarantees log delivery even when the
                event loop is busy. Default is False (direct writes).
        """
        super().__init__()
        self._storage = storage
        self._include_attrs = include_attrs or _DEFAULT_INCLUDE_ATTRS
        self._context_provider = context_provider
        self._background_writer = background_writer

        # Background writer state
        self._queue: queue.Queue[LogEntry | None] | None = None
        self._writer_thread: threading.Thread | None = None

        if background_writer:
            self._queue = queue.Queue()
            self._writer_thread = threading.Thread(
                target=self._background_write_loop,
                daemon=False,  # Ensure graceful shutdown
            )
            self._writer_thread.start()

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

        # Start with context provider attributes (lowest precedence)
        attributes: dict[str, str | int | float | bool] = {}
        if self._context_provider is not None:
            attributes = self._context_provider().copy()

        # Add attributes based on include_attrs configuration (overrides context)
        for key in self._include_attrs:
            if key in attr_mapping:
                attributes[key] = attr_mapping[key]

        # Add any extra attributes passed via logging call (highest precedence)
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

        if self._background_writer and self._queue is not None:
            self._queue.put(entry)
        else:
            self._write_to_storage(entry)

    def _write_to_storage(self, entry: LogEntry) -> None:
        """Write entry to storage, handling sync/async contexts.

        Detects whether we're inside a running event loop and schedules
        the write appropriately.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop - use asyncio.run() (sync context)
            asyncio.run(self._storage.write(entry))
        else:
            # Inside a running event loop - schedule as a task
            loop.create_task(self._storage.write(entry))

    def _background_write_loop(self) -> None:
        """Background thread that processes the write queue."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            assert self._queue is not None
            entry = self._queue.get()
            if entry is None:  # Shutdown signal
                self._queue.task_done()
                break
            loop.run_until_complete(self._storage.write(entry))
            self._queue.task_done()

        loop.close()

    def flush(self) -> None:
        """Block until all queued writes are drained.

        For background_writer=True, this blocks until the queue is empty
        and all writes have completed. For background_writer=False, this
        is a no-op since writes are synchronous.
        """
        if self._background_writer and self._queue is not None:
            self._queue.join()
        super().flush()

    def close(self) -> None:
        """Close the handler, flushing any pending writes."""
        if self._background_writer and self._queue is not None:
            self._queue.put(None)  # Shutdown signal
            if self._writer_thread is not None:
                self._writer_thread.join(timeout=5.0)
        super().close()
