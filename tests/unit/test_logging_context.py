"""Unit tests for logging context helper."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

# Import will fail until we implement the module - that's expected for RED phase
from observabilipy.adapters.logging_context import (
    clear_log_context,
    get_log_context,
    log_context,
    set_log_context,
    update_log_context,
)


@pytest.mark.core
class TestLoggingContext:
    """Tests for logging context helper functions."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_log_context()

    def test_get_log_context_default_empty(self) -> None:
        """get_log_context returns empty dict by default."""
        assert get_log_context() == {}

    def test_set_log_context(self) -> None:
        """set_log_context replaces current context."""
        set_log_context(user_id=42, request_id="abc")
        assert get_log_context() == {"user_id": 42, "request_id": "abc"}

    def test_set_log_context_replaces(self) -> None:
        """set_log_context replaces, not merges."""
        set_log_context(a=1, b=2)
        set_log_context(c=3)
        assert get_log_context() == {"c": 3}

    def test_update_log_context(self) -> None:
        """update_log_context merges into existing."""
        set_log_context(a=1)
        update_log_context(b=2)
        assert get_log_context() == {"a": 1, "b": 2}

    def test_update_log_context_overwrites_existing(self) -> None:
        """update_log_context overwrites existing keys."""
        set_log_context(a=1)
        update_log_context(a=2)
        assert get_log_context() == {"a": 2}

    def test_clear_log_context(self) -> None:
        """clear_log_context removes all attributes."""
        set_log_context(a=1, b=2)
        clear_log_context()
        assert get_log_context() == {}

    def test_log_context_manager_adds_attrs(self) -> None:
        """log_context adds attributes for duration of block."""
        with log_context(request_id="req-123"):
            assert get_log_context()["request_id"] == "req-123"

    def test_log_context_manager_restores_on_exit(self) -> None:
        """log_context restores previous context on exit."""
        set_log_context(outer="value")
        with log_context(inner="temp"):
            assert "inner" in get_log_context()
        assert get_log_context() == {"outer": "value"}

    def test_log_context_manager_nested(self) -> None:
        """Nested log_context blocks work correctly."""
        with log_context(level1="a"):
            with log_context(level2="b"):
                ctx = get_log_context()
                assert ctx["level1"] == "a"
                assert ctx["level2"] == "b"
            assert get_log_context() == {"level1": "a"}
        assert get_log_context() == {}

    def test_log_context_manager_exception_restores(self) -> None:
        """log_context restores context even on exception."""
        set_log_context(before="error")
        try:
            with log_context(during="exception"):
                raise ValueError("test")
        except ValueError:
            pass
        assert get_log_context() == {"before": "error"}

    def test_get_log_context_returns_copy(self) -> None:
        """get_log_context returns a copy, not reference."""
        set_log_context(a=1)
        ctx = get_log_context()
        ctx["b"] = 2
        assert get_log_context() == {"a": 1}  # Original unchanged

    async def test_context_isolated_per_task(self) -> None:
        """Context is isolated per asyncio task."""
        results: list[str | None] = []

        async def task(task_id: str) -> None:
            with log_context(task_id=task_id):
                await asyncio.sleep(0.01)
                results.append(get_log_context().get("task_id"))  # type: ignore[arg-type]

        await asyncio.gather(task("task1"), task("task2"))

        # Each task should have seen its own context
        assert "task1" in results
        assert "task2" in results

    def test_context_isolated_per_thread(self) -> None:
        """Context is isolated per thread."""
        results: list[str | None] = []

        def thread_fn(thread_id: str) -> None:
            with log_context(thread_id=thread_id):
                results.append(get_log_context().get("thread_id"))  # type: ignore[arg-type]

        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(thread_fn, "thread1")
            executor.submit(thread_fn, "thread2")
            executor.shutdown(wait=True)

        assert "thread1" in results
        assert "thread2" in results
