"""Tests for EmbeddedRuntime orchestrator."""

import pytest

from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.exceptions import ConfigurationError
from observabilipy.core.models import (
    LevelRetentionPolicy,
    LogEntry,
    MetricSample,
    RetentionPolicy,
)
from observabilipy.runtime.embedded import EmbeddedRuntime


@pytest.mark.runtime
class TestEmbeddedRuntimeValidation:
    """Tests for runtime configuration validation."""

    def test_rejects_zero_cleanup_interval(self) -> None:
        """cleanup_interval_seconds=0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EmbeddedRuntime(cleanup_interval_seconds=0.0)
        assert "cleanup_interval_seconds" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_cleanup_interval(self) -> None:
        """Negative cleanup_interval_seconds raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            EmbeddedRuntime(cleanup_interval_seconds=-1.0)


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
        samples = [s async for s in storage.read()]
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


@pytest.mark.runtime
class TestEmbeddedRuntimePerLevelRetention:
    """Tests for per-level retention cleanup logic."""

    async def test_run_once_applies_different_policies_per_level(self) -> None:
        """Different levels have different retention applied."""
        storage = InMemoryLogStorage()
        # ERROR at 100, INFO at 100, ERROR at 300, INFO at 300
        await storage.write(
            LogEntry(timestamp=100.0, level="ERROR", message="old error")
        )
        await storage.write(LogEntry(timestamp=100.0, level="INFO", message="old info"))
        await storage.write(
            LogEntry(timestamp=300.0, level="ERROR", message="new error")
        )
        await storage.write(LogEntry(timestamp=300.0, level="INFO", message="new info"))

        # ERROR: keep 250 seconds (threshold: 400-250=150, so 100 deleted)
        # INFO: keep 100 seconds (threshold: 400-100=300, so 100 deleted)
        policy = LevelRetentionPolicy(
            policies={
                "ERROR": RetentionPolicy(max_age_seconds=250.0),
                "INFO": RetentionPolicy(max_age_seconds=100.0),
            }
        )
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 400.0,
        )

        await runtime.run_once()

        entries = [e async for e in storage.read()]
        # ERROR at 100 deleted (< 150), ERROR at 300 kept
        # INFO at 100 deleted (< 300), INFO at 300 kept
        assert len(entries) == 2
        assert any(e.level == "ERROR" and e.timestamp == 300.0 for e in entries)
        assert any(e.level == "INFO" and e.timestamp == 300.0 for e in entries)

    async def test_run_once_uses_default_policy_for_unconfigured_level(self) -> None:
        """Levels not in policies use default policy."""
        storage = InMemoryLogStorage()
        await storage.write(
            LogEntry(timestamp=100.0, level="DEBUG", message="old debug")
        )
        await storage.write(
            LogEntry(timestamp=300.0, level="DEBUG", message="new debug")
        )

        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_age_seconds=1000.0)},
            default=RetentionPolicy(max_age_seconds=150.0),  # threshold: 400-150=250
        )
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 400.0,
        )

        await runtime.run_once()

        entries = [e async for e in storage.read()]
        assert len(entries) == 1
        assert entries[0].timestamp == 300.0

    async def test_run_once_skips_level_without_policy_or_default(self) -> None:
        """Levels without policy and no default are not cleaned up."""
        storage = InMemoryLogStorage()
        await storage.write(
            LogEntry(timestamp=100.0, level="TRACE", message="old trace")
        )
        await storage.write(
            LogEntry(timestamp=100.0, level="ERROR", message="old error")
        )

        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_age_seconds=150.0)},
            # No default - TRACE has no policy
        )
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 400.0,
        )

        await runtime.run_once()

        entries = [e async for e in storage.read()]
        # ERROR at 100 deleted (< 250 threshold)
        # TRACE at 100 kept (no policy)
        assert len(entries) == 1
        assert entries[0].level == "TRACE"

    async def test_run_once_applies_count_limit_per_level(self) -> None:
        """Count limits are applied per level independently."""
        storage = InMemoryLogStorage()
        # 3 ERROR, 3 INFO entries
        for i in range(3):
            await storage.write(
                LogEntry(timestamp=100.0 + i, level="ERROR", message=f"e{i}")
            )
            await storage.write(
                LogEntry(timestamp=100.0 + i, level="INFO", message=f"i{i}")
            )

        policy = LevelRetentionPolicy(
            policies={
                "ERROR": RetentionPolicy(max_count=2),  # Keep newest 2 ERROR
                "INFO": RetentionPolicy(max_count=1),  # Keep newest 1 INFO
            }
        )
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
        )

        await runtime.run_once()

        entries = [e async for e in storage.read()]
        error_entries = [e for e in entries if e.level == "ERROR"]
        info_entries = [e for e in entries if e.level == "INFO"]

        assert len(error_entries) == 2
        assert len(info_entries) == 1

    async def test_backward_compatible_with_single_retention_policy(self) -> None:
        """Single RetentionPolicy still works (backward compatibility)."""
        storage = InMemoryLogStorage()
        await storage.write(LogEntry(timestamp=100.0, level="ERROR", message="old"))
        await storage.write(LogEntry(timestamp=300.0, level="INFO", message="new"))

        # Old-style single policy
        policy = RetentionPolicy(max_age_seconds=150.0)
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 400.0,
        )

        await runtime.run_once()

        # Both levels treated the same, threshold = 250
        entries = [e async for e in storage.read()]
        assert len(entries) == 1
        assert entries[0].timestamp == 300.0

    async def test_run_once_applies_combined_age_and_count_per_level(self) -> None:
        """Both age and count policies can be applied per level."""
        storage = InMemoryLogStorage()
        # 5 ERROR entries
        for i in range(5):
            await storage.write(
                LogEntry(timestamp=100.0 * (i + 1), level="ERROR", message=f"e{i}")
            )

        # Age: delete older than 250 (600 - 350) -> keeps 300, 400, 500
        # Count: max 2 -> keeps 400, 500
        policy = LevelRetentionPolicy(
            policies={
                "ERROR": RetentionPolicy(max_age_seconds=350.0, max_count=2),
            }
        )
        runtime = EmbeddedRuntime(
            log_storage=storage,
            log_retention=policy,
            time_func=lambda: 600.0,
        )

        await runtime.run_once()

        entries = [e async for e in storage.read()]
        assert len(entries) == 2
        timestamps = sorted(e.timestamp for e in entries)
        assert timestamps == [400.0, 500.0]
