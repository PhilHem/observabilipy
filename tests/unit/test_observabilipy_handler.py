"""Unit tests for ObservabilipyHandler logging adapter."""

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
class TestObservabilipyHandler:
    """Tests for ObservabilipyHandler adapter."""

    def test_handler_is_logging_handler(self) -> None:
        """Handler extends logging.Handler."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)
        assert isinstance(handler, logging.Handler)

    def test_emit_writes_log_entry(self) -> None:
        """Handler.emit() writes LogEntry to storage."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1
        assert entries[0].message == "test message"
        assert entries[0].level == "INFO"

    def test_extracts_logrecord_attributes(self) -> None:
        """Handler extracts module, funcName, lineno from LogRecord."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        record = logging.LogRecord(
            name="myapp.service",
            level=logging.ERROR,
            pathname="/app/service.py",
            lineno=42,
            msg="error occurred",
            args=(),
            exc_info=None,
            func="process_request",
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert entries[0].attributes["module"] == "myapp.service"
        assert entries[0].attributes["funcName"] == "process_request"
        assert entries[0].attributes["lineno"] == 42
        assert entries[0].attributes["pathname"] == "/app/service.py"

    def test_includes_extra_attributes(self) -> None:
        """Handler includes extra dict from logging call."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)
        logger = logging.getLogger("test_extra")
        logger.handlers.clear()  # Remove any existing handlers
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("request processed", extra={"request_id": "abc123", "user_id": 42})

        entries = _run_async(_collect_entries(storage))
        assert entries[0].attributes["request_id"] == "abc123"
        assert entries[0].attributes["user_id"] == 42

    def test_extracts_exception_info(self) -> None:
        """Handler extracts exception info when present."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)
        logger = logging.getLogger("test_exception")
        logger.handlers.clear()
        logger.addHandler(handler)

        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception("caught error")

        entries = _run_async(_collect_entries(storage))
        assert "exc_type" in entries[0].attributes
        assert entries[0].attributes["exc_type"] == "ValueError"
        assert "exc_message" in entries[0].attributes
        assert entries[0].attributes["exc_message"] == "test error"
        assert "exc_traceback" in entries[0].attributes
        assert "ValueError: test error" in entries[0].attributes["exc_traceback"]

    def test_configurable_attributes(self) -> None:
        """Handler allows configuring which LogRecord fields to include."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(
            storage,
            include_attrs=["module", "lineno"],  # Only these two
        )

        record = logging.LogRecord(
            name="myapp",
            level=logging.INFO,
            pathname="/app/main.py",
            lineno=10,
            msg="test",
            args=(),
            exc_info=None,
            func="main",
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert "module" in entries[0].attributes
        assert "lineno" in entries[0].attributes
        assert "funcName" not in entries[0].attributes
        assert "pathname" not in entries[0].attributes

    def test_context_provider_merges_attributes(self) -> None:
        """Context provider attributes are merged into log entry."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(
            storage,
            context_provider=lambda: {"request_id": "abc", "env": "test"},
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert entries[0].attributes["request_id"] == "abc"
        assert entries[0].attributes["env"] == "test"

    def test_extra_overrides_context_provider(self) -> None:
        """Extra attributes override context provider values."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(
            storage,
            context_provider=lambda: {"user_id": "from_context"},
        )
        logger = logging.getLogger("test_override")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("test", extra={"user_id": "from_extra"})

        entries = _run_async(_collect_entries(storage))
        assert entries[0].attributes["user_id"] == "from_extra"

    def test_context_provider_not_called_when_none(self) -> None:
        """Handler works normally when context_provider is None."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)  # No context_provider

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="no context",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1
        # Only standard attrs, no context
        assert "request_id" not in entries[0].attributes

    def test_context_provider_empty_dict(self) -> None:
        """Context provider returning empty dict works correctly."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(
            storage,
            context_provider=lambda: {},
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="empty context",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1


@pytest.mark.core
class TestPackageExports:
    """Tests for package-level exports."""

    def test_context_provider_importable_from_package(self) -> None:
        """ContextProvider type alias is importable from observabilipy."""
        from observabilipy import ContextProvider as PkgContextProvider
        from observabilipy.adapters.logging import ContextProvider

        assert PkgContextProvider is ContextProvider
