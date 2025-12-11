"""Tests for EmbeddedRuntime orchestrator."""

import pytest

from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample, RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime


@pytest.mark.runtime
class TestEmbeddedRuntimeLifecycle:
    """Tests for runtime lifecycle management."""

    async def test_can_start_and_stop(self) -> None:
        runtime = EmbeddedRuntime()
        await runtime.start()
        await runtime.stop()

    async def test_context_manager_starts_and_stops(self) -> None:
        async with EmbeddedRuntime():
            pass

    async def test_stop_is_idempotent(self) -> None:
        runtime = EmbeddedRuntime()
        await runtime.start()
        await runtime.stop()
        await runtime.stop()  # Should not raise


@pytest.mark.runtime
class TestEmbeddedRuntimeRetention:
    """Tests for retention cleanup logic."""

    async def test_run_once_deletes_old_logs_by_age(self) -> None:
        storage = InMemoryLogStorage()
        # Add entries at different timestamps
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="old"))
        await storage.write(LogEntry(timestamp=200.0, level="INFO", message="medium"))
        await storage.write(LogEntry(timestamp=300.0, level="INFO", message="new"))

        policy = RetentionPolicy(max_age_seconds=150.0)
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 400.0,  # Current time is 400
        )

        await runtime.run_once()

        # Only entries >= 250 (400 - 150) should remain
        assert await storage.count() == 1

    async def test_run_once_deletes_old_metrics_by_age(self) -> None:
        storage = InMemoryMetricsStorage()
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))
        await storage.write(MetricSample(name="m", timestamp=200.0, value=2.0))
        await storage.write(MetricSample(name="m", timestamp=300.0, value=3.0))

        policy = RetentionPolicy(max_age_seconds=150.0)
        runtime = EmbeddedRuntime(
            metrics_storage=storage,
            metrics_retention=policy,
            time_func=lambda: 400.0,
        )

        await runtime.run_once()

        assert await storage.count() == 1

    async def test_run_once_does_nothing_without_policy(self) -> None:
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(LogEntry(timestamp=100.0, level="INFO", message="old"))
        await metrics_storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))

        runtime = EmbeddedRuntime(
            log_storage=log_storage,
            metrics_storage=metrics_storage,
            time_func=lambda: 1000.0,  # Way in the future
        )

        await runtime.run_once()

        # No policy, so nothing deleted
        assert await log_storage.count() == 1
        assert await metrics_storage.count() == 1

    async def test_run_once_deletes_oldest_logs_when_over_count_limit(self) -> None:
        storage = InMemoryLogStorage()
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="oldest"))
        await storage.write(LogEntry(timestamp=200.0, level="INFO", message="middle"))
        await storage.write(LogEntry(timestamp=300.0, level="INFO", message="newest"))

        policy = RetentionPolicy(max_count=2)
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
        )

        await runtime.run_once()

        # Should keep only 2 newest entries
        assert await storage.count() == 2
        entries = [e async for e in storage.read()]
        assert entries[0].message == "middle"
        assert entries[1].message == "newest"

    async def test_run_once_deletes_oldest_metrics_when_over_count_limit(self) -> None:
        storage = InMemoryMetricsStorage()
        await storage.write(MetricSample(name="m", timestamp=100.0, value=1.0))
        await storage.write(MetricSample(name="m", timestamp=200.0, value=2.0))
        await storage.write(MetricSample(name="m", timestamp=300.0, value=3.0))

        policy = RetentionPolicy(max_count=2)
        runtime = EmbeddedRuntime(
            metrics_storage=storage,
            metrics_retention=policy,
        )

        await runtime.run_once()

        assert await storage.count() == 2
        samples = [s async for s in storage.scrape()]
        values = sorted(s.value for s in samples)
        assert values == [2.0, 3.0]

    async def test_run_once_applies_both_age_and_count(self) -> None:
        storage = InMemoryLogStorage()
        # 5 entries, will apply both policies
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="1"))
        await storage.write(LogEntry(timestamp=200.0, level="INFO", message="2"))
        await storage.write(LogEntry(timestamp=300.0, level="INFO", message="3"))
        await storage.write(LogEntry(timestamp=400.0, level="INFO", message="4"))
        await storage.write(LogEntry(timestamp=500.0, level="INFO", message="5"))

        # Age policy: delete entries older than 250 (current 600 - 350 = 250)
        # Count policy: keep max 3
        policy = RetentionPolicy(max_age_seconds=350.0, max_count=3)
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 600.0,
        )

        await runtime.run_once()

        # Age threshold is 250, so entries 1, 2 deleted (timestamps 100, 200)
        # Then count check: 3 remain, which is exactly max_count, so no more deletion
        assert await storage.count() == 3
