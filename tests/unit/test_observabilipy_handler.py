"""Unit tests for ObservabilipyHandler logging adapter."""

import asyncio
import logging
import threading
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
class TestAsyncAwareEmit:
    """Tests for async-aware emit() behavior."""

    def test_emit_works_without_running_event_loop(self) -> None:
        """emit() works when called outside any event loop (regression test)."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="sync context message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1
        assert entries[0].message == "sync context message"

    def test_emit_works_inside_running_event_loop(self) -> None:
        """emit() works when called from inside an already-running event loop."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)
        emit_called = threading.Event()
        emit_error: list[Exception] = []

        def run_in_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def async_main() -> None:
                # We are now inside a running event loop
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="async context message",
                    args=(),
                    exc_info=None,
                )
                try:
                    handler.emit(record)
                except Exception as e:
                    emit_error.append(e)
                emit_called.set()
                # Give time for any scheduled tasks to complete
                await asyncio.sleep(0.1)

            loop.run_until_complete(async_main())
            loop.close()

        thread = threading.Thread(target=run_in_loop)
        thread.start()
        thread.join(timeout=2.0)

        assert emit_called.is_set(), "emit() was never called"
        assert len(emit_error) == 0, f"emit() raised: {emit_error[0]}"

        # Verify the entry was written
        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1
        assert entries[0].message == "async context message"


@pytest.mark.core
class TestBackgroundWriter:
    """Tests for optional background writer mode."""

    def test_background_writer_handles_high_volume(self) -> None:
        """Background writer queues logs and writes them asynchronously."""
        import time

        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, background_writer=True)

        # Log many messages rapidly
        for i in range(100):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        # Give background thread time to process
        time.sleep(0.5)
        handler.close()

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 100

    def test_handler_close_flushes_pending_writes(self) -> None:
        """handler.close() flushes all pending writes before returning."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, background_writer=True)

        # Log several messages
        for i in range(10):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        # Close handler (should flush)
        handler.close()

        # All entries should be present immediately after close
        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 10

    def test_background_writer_thread_safety(self) -> None:
        """Background writer handles concurrent emit() from multiple threads."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, background_writer=True)

        def log_from_thread(thread_id: int) -> None:
            for i in range(10):
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"thread-{thread_id}-message-{i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)

        threads = [
            threading.Thread(target=log_from_thread, args=(i,)) for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        handler.close()

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 50  # 5 threads * 10 messages

    def test_background_writer_default_is_false(self) -> None:
        """background_writer defaults to False (sync behavior)."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage)

        # Should not have background writer attributes
        assert not hasattr(handler, "_queue") or handler._queue is None
        assert not hasattr(handler, "_writer_thread") or handler._writer_thread is None

    def test_flush_blocks_until_queue_drained(self) -> None:
        """flush() blocks until all queued writes complete."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, background_writer=True)

        # Log several messages
        for i in range(10):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        # Flush (should block until queue drained)
        handler.flush()

        # All entries should be present immediately after flush
        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 10

        handler.close()

    def test_flush_noop_without_background_writer(self) -> None:
        """flush() is safe to call when background_writer=False."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, background_writer=False)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        # Should not raise
        handler.flush()

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1

        handler.close()

    def test_flush_can_be_called_multiple_times(self) -> None:
        """flush() can be called repeatedly without issues."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, background_writer=True)

        for batch in range(3):
            for i in range(5):
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="test.py",
                    lineno=1,
                    msg=f"batch {batch} message {i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)
            handler.flush()

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 15

        handler.close()


@pytest.mark.core
class TestPackageExports:
    """Tests for package-level exports."""

    def test_context_provider_importable_from_package(self) -> None:
        """ContextProvider type alias is importable from observabilipy."""
        from observabilipy import ContextProvider as PkgContextProvider
        from observabilipy.adapters.logging import ContextProvider

        assert PkgContextProvider is ContextProvider
