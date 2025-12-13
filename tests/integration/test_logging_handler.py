"""Integration tests for ObservabilipyHandler logging adapter."""

import asyncio
import logging
from typing import Any

import pytest

from observabilipy.adapters.logging import ObservabilipyHandler
from observabilipy.adapters.storage.in_memory import InMemoryLogStorage


def _run_async(coro: Any) -> Any:
    """Run a coroutine in a new event loop (for sync test helpers)."""
    return asyncio.run(coro)


async def _collect_entries(storage: InMemoryLogStorage) -> list[Any]:
    """Collect all entries from storage."""
    return [e async for e in storage.read()]


@pytest.mark.core
class TestLoggingHandlerIntegration:
    """Integration tests for ObservabilipyHandler with Python's logging system."""

    def test_real_logger_flow(self) -> None:
        """Full integration with Python's logging system."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        logger = logging.getLogger("integration_test")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 4
        assert [e.level for e in entries] == ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert [e.message for e in entries] == [
            "debug msg",
            "info msg",
            "warning msg",
            "error msg",
        ]

    def test_logger_with_format_args(self) -> None:
        """Logger correctly formats messages with arguments."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        logger = logging.getLogger("format_test")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("User %s logged in from %s", "alice", "192.168.1.1")

        entries = _run_async(_collect_entries(storage))
        assert entries[0].message == "User alice logged in from 192.168.1.1"

    def test_child_loggers_propagate(self) -> None:
        """Child loggers propagate to parent with our handler."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        parent_logger = logging.getLogger("myapp_test")
        parent_logger.handlers.clear()
        parent_logger.addHandler(handler)
        parent_logger.setLevel(logging.DEBUG)

        child_logger = logging.getLogger("myapp_test.database")
        child_logger.info("Database connected")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1
        assert entries[0].message == "Database connected"
        assert entries[0].attributes["module"] == "myapp_test.database"

    def test_timestamps_are_preserved(self) -> None:
        """Handler preserves LogRecord timestamps."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        logger = logging.getLogger("timestamp_test")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("test message")

        entries = _run_async(_collect_entries(storage))
        # Timestamp should be a recent Unix timestamp (seconds since epoch)
        assert entries[0].timestamp > 1700000000  # After Nov 2023
        assert entries[0].timestamp < 2000000000  # Before 2033
