"""Event observability adapter for recording domain events."""

import asyncio
from collections.abc import Iterable
from typing import Any

from observabilipy.core.events.registry import MappingRegistry
from observabilipy.core.models import LogEntry, MetricSample
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


class EventObservability:
    """Adapter for recording domain events as observability data.

    Bridges domain events to the observability system by using registered
    mapping functions to convert events into logs and metrics.

    Handles both synchronous and asynchronous contexts automatically
    by detecting whether an event loop is running.

    Example:
        >>> import asyncio
        >>> from observabilipy import (
        ...     EventObservability,
        ...     MappingRegistry,
        ...     InMemoryLogStorage,
        ...     InMemoryMetricsStorage,
        ...     LogEntry,
        ... )
        >>> registry = MappingRegistry()
        >>> def mapper(event):
        ...     return [LogEntry(timestamp=1.0, level="INFO", message="Event")]
        >>> registry.register("MyEvent", mapper)
        >>> adapter = EventObservability(
        ...     registry,
        ...     InMemoryLogStorage(),
        ...     InMemoryMetricsStorage(),
        ... )
    """

    def __init__(
        self,
        registry: MappingRegistry,
        log_storage: LogStoragePort,
        metrics_storage: MetricsStoragePort,
        *,
        sync: bool = False,
    ) -> None:
        """Initialize the event observability adapter.

        Args:
            registry: Registry containing event-to-observability mappings.
            log_storage: Storage backend for log entries.
            metrics_storage: Storage backend for metric samples.
            sync: If True, writes to storage synchronously bypassing async
                machinery. Useful for testing and WSGI contexts where
                fire-and-forget tasks would cause race conditions.
        """
        self._registry = registry
        self._log_storage = log_storage
        self._metrics_storage = metrics_storage
        self._sync = sync

    def record(self, event: Any) -> None:
        """Record a domain event synchronously.

        Looks up the mapper for the event's class name, invokes it,
        and writes the outputs to storage. Handles both sync and async
        contexts automatically.

        If no mapper is registered for the event type, the event is
        silently ignored (no error raised).

        Args:
            event: The domain event instance to record.
        """
        event_class = type(event).__name__
        mapper = self._registry.lookup(event_class)
        if mapper is None:
            return  # Silently ignore unmapped events

        outputs = list(mapper(event))  # Materialize iterable
        self._write_outputs(outputs)

    async def record_async(self, event: Any) -> None:
        """Record a domain event asynchronously.

        Async version of record() for use in async contexts.

        Args:
            event: The domain event instance to record.
        """
        event_class = type(event).__name__
        mapper = self._registry.lookup(event_class)
        if mapper is None:
            return

        outputs = list(mapper(event))
        await self._write_outputs_async(outputs)

    def _write_outputs(self, outputs: list[LogEntry | MetricSample]) -> None:
        """Write outputs to storage, handling sync/async contexts.

        When sync=True, writes directly to storage lists bypassing async.
        Otherwise, detects whether we're inside a running event loop and
        schedules the write appropriately.
        """
        if self._sync:
            # Synchronous write - uses write_sync() method
            # Only works with InMemoryStorage (intended for testing)
            for output in outputs:
                if isinstance(output, LogEntry):
                    self._log_storage.write_sync(output)  # type: ignore[attr-defined]
                elif isinstance(output, MetricSample):
                    self._metrics_storage.write_sync(output)  # type: ignore[attr-defined]
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop - use asyncio.run() (sync context)
            asyncio.run(self._write_outputs_async(outputs))
        else:
            # Inside a running event loop - schedule as a task
            loop.create_task(self._write_outputs_async(outputs))

    async def _write_outputs_async(
        self, outputs: Iterable[LogEntry | MetricSample]
    ) -> None:
        """Write outputs to appropriate storage backends.

        Args:
            outputs: Iterable of LogEntry and/or MetricSample objects.
        """
        for output in outputs:
            if isinstance(output, LogEntry):
                await self._log_storage.write(output)
            elif isinstance(output, MetricSample):
                await self._metrics_storage.write(output)
