"""Integration tests for EmbeddedRuntime with real storage adapters."""

import asyncio

import pytest

from observabilipy.adapters.storage.in_memory import InMemoryLogStorage
from observabilipy.core.models import LogEntry, RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime


@pytest.mark.runtime
class TestEmbeddedRuntimeBackgroundTask:
    """Tests for background cleanup task behavior."""

    async def test_background_task_runs_cleanup_at_interval(self) -> None:
        storage = InMemoryLogStorage()
        current_time = 100.0

        def mock_time() -> float:
            return current_time

        # Add an old entry that will be deleted
        await storage.write(LogEntry(timestamp=50.0, level="INFO", message="old"))

        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=RetentionPolicy(max_age_seconds=30.0),
            cleanup_interval_seconds=0.05,  # 50ms interval for fast test
            time_func=mock_time,
        )

        await runtime.start()
        # Wait for at least one cleanup cycle
        await asyncio.sleep(0.1)
        await runtime.stop()

        # Entry should have been deleted by background task
        assert await storage.count() == 0

    async def test_graceful_shutdown_cancels_background_task(self) -> None:
        runtime = EmbeddedRuntime(cleanup_interval_seconds=10.0)
        await runtime.start()

        # Task should be running
        assert runtime._task is not None
        assert not runtime._task.done()

        await runtime.stop()

        # Task should be cancelled and cleaned up
        assert runtime._task is None

    async def test_context_manager_cleanup_on_exception(self) -> None:
        storage = InMemoryLogStorage()
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=RetentionPolicy(max_age_seconds=60.0),
        )

        with pytest.raises(ValueError, match="test error"):
            async with runtime:
                raise ValueError("test error")

        # Runtime should be stopped even after exception
        assert runtime._running is False
        assert runtime._task is None

    async def test_multiple_start_calls_are_idempotent(self) -> None:
        runtime = EmbeddedRuntime()
        await runtime.start()
        task1 = runtime._task

        await runtime.start()  # Second start should be no-op
        task2 = runtime._task

        # Should be the same task
        assert task1 is task2
        await runtime.stop()
