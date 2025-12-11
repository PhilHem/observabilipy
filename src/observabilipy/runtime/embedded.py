"""Embedded runtime orchestrator for observability."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from observabilipy.core.models import LogEntry, MetricSample, RetentionPolicy
from observabilipy.core.retention import calculate_age_threshold, should_delete_by_count

if TYPE_CHECKING:
    from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


class EmbeddedRuntime:
    """Orchestrates lifecycle and background retention cleanup.

    Manages storage adapters and runs periodic retention cleanup based on
    configured policies. Supports both age-based and count-based retention.

    Example:
        async with EmbeddedRuntime(
            log_storage=storage,
            log_retention=RetentionPolicy(max_age_seconds=3600),
            cleanup_interval_seconds=60,
        ):
            # Runtime is active, cleanup runs in background
            ...
    """

    def __init__(
        self,
        log_storage: LogStoragePort | None = None,
        log_retention: RetentionPolicy | None = None,
        metrics_storage: MetricsStoragePort | None = None,
        metrics_retention: RetentionPolicy | None = None,
        cleanup_interval_seconds: float = 60.0,
        time_func: Callable[[], float] = time.time,
    ) -> None:
        """Initialize the embedded runtime.

        Args:
            log_storage: Storage adapter for logs. None skips log retention.
            log_retention: Retention policy for logs. None skips cleanup.
            metrics_storage: Storage adapter for metrics. None skips retention.
            metrics_retention: Retention policy for metrics. None skips cleanup.
            cleanup_interval_seconds: How often to run cleanup (default 60s).
            time_func: Function returning current time as float (for testing).
        """
        self._log_storage = log_storage
        self._log_retention = log_retention
        self._metrics_storage = metrics_storage
        self._metrics_retention = metrics_retention
        self._cleanup_interval = cleanup_interval_seconds
        self._time_func = time_func
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the background cleanup task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the background cleanup task."""
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def run_once(self) -> None:
        """Run a single cleanup cycle.

        Applies retention policies to both logs and metrics storage.
        Useful for testing or manual cleanup triggers.
        """
        await self._apply_retention(
            self._log_storage,
            self._log_retention,
            is_logs=True,
        )
        await self._apply_retention(
            self._metrics_storage,
            self._metrics_retention,
            is_logs=False,
        )

    async def _apply_retention(
        self,
        storage: LogStoragePort | MetricsStoragePort | None,
        policy: RetentionPolicy | None,
        is_logs: bool,
    ) -> None:
        """Apply retention policy to a storage adapter."""
        if storage is None or policy is None:
            return

        # Age-based retention
        threshold = calculate_age_threshold(policy, self._time_func())
        if threshold is not None:
            await storage.delete_before(threshold)

        # Count-based retention
        current_count = await storage.count()
        needs_count_deletion = should_delete_by_count(policy, current_count)
        if needs_count_deletion and policy.max_count is not None:
            # Find the timestamp threshold to keep only max_count entries
            entries = await self._collect_entries(storage, is_logs)
            if len(entries) > policy.max_count:
                # Sort by timestamp descending, keep newest max_count
                entries.sort(key=lambda e: e.timestamp, reverse=True)
                # The oldest entry we keep has this timestamp
                oldest_to_keep = entries[policy.max_count - 1].timestamp
                # Delete everything older than the oldest we keep
                await storage.delete_before(oldest_to_keep)

    async def _collect_entries(
        self,
        storage: LogStoragePort | MetricsStoragePort,
        is_logs: bool,
    ) -> list[LogEntry] | list[MetricSample]:
        """Collect all entries from storage."""
        if is_logs:
            return [e async for e in storage.read()]  # type: ignore[union-attr]
        else:
            return [s async for s in storage.scrape()]  # type: ignore[union-attr]

    async def _cleanup_loop(self) -> None:
        """Background loop that periodically runs cleanup."""
        while self._running:
            await self.run_once()
            await asyncio.sleep(self._cleanup_interval)

    async def __aenter__(self) -> EmbeddedRuntime:
        """Enter async context manager."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        await self.stop()
