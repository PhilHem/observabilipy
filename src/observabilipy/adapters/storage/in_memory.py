"""In-memory storage adapters for logs and metrics."""

from collections.abc import AsyncIterable
from typing import Protocol, runtime_checkable

from observabilipy.core.models import LogEntry, MetricSample


@runtime_checkable
class Timestamped(Protocol):
    """Protocol for items with a timestamp attribute.

    This internal protocol enables generic storage implementations
    that filter and sort by timestamp.
    """

    @property
    def timestamp(self) -> float: ...


class InMemoryStorage[T: Timestamped]:
    """Generic base class for in-memory storage.

    Provides common operations for storing timestamped items in a list.
    Subclasses implement type-specific read() methods.
    """

    def __init__(self) -> None:
        self._items: list[T] = []

    async def write(self, item: T) -> None:
        """Write an item to storage."""
        self._items.append(item)

    def write_sync(self, item: T) -> None:
        """Synchronous write for testing contexts."""
        self._items.append(item)

    def write_sync_batch(self, items: list[T]) -> None:
        """Synchronous batch write for testing contexts."""
        self._items.extend(items)

    async def clear(self) -> None:
        """Clear all items from storage."""
        self._items.clear()

    def clear_sync(self) -> None:
        """Synchronous clear for testing contexts."""
        self._items.clear()

    async def count(self) -> int:
        """Return total number of items in storage."""
        return len(self._items)

    async def delete_before(self, timestamp: float) -> int:
        """Delete items with timestamp < given value."""
        original_count = len(self._items)
        self._items = [item for item in self._items if item.timestamp >= timestamp]
        return original_count - len(self._items)

    def _read_since(self, since: float) -> list[T]:
        """Return items with timestamp > since, sorted by timestamp.

        Protected helper for subclass read() implementations.
        """
        filtered = [item for item in self._items if item.timestamp > since]
        return sorted(filtered, key=lambda item: item.timestamp)


class InMemoryLogStorage(InMemoryStorage[LogEntry]):
    """In-memory implementation of LogStoragePort.

    Stores log entries in a list. Suitable for testing and
    low-volume applications where persistence is not required.

    Example:
        >>> import asyncio
        >>> from observabilipy import InMemoryLogStorage, LogEntry
        >>> async def demo():
        ...     storage = InMemoryLogStorage()
        ...     entry = LogEntry(timestamp=1.0, level="INFO", message="test")
        ...     await storage.write(entry)
        ...     return await storage.count()
        >>> asyncio.run(demo())
        1
    """

    @property
    def _entries(self) -> list[LogEntry]:
        """Alias for _items to maintain backward compatibility with tests."""
        return self._items

    async def read(
        self, since: float = 0, level: str | None = None
    ) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp, optionally filtered by level.

        Returns entries with timestamp > since, ordered by timestamp ascending.
        If level is provided, only entries with matching level (case-insensitive)
        are returned.
        """
        entries = self._read_since(since)
        if level is not None:
            level_upper = level.upper()
            entries = [e for e in entries if e.level.upper() == level_upper]
        for entry in entries:
            yield entry

    async def delete_by_level_before(self, level: str, timestamp: float) -> int:
        """Delete log entries matching level with timestamp < given value."""
        original_count = len(self._items)
        self._items = [
            e for e in self._items if not (e.level == level and e.timestamp < timestamp)
        ]
        return original_count - len(self._items)

    async def count_by_level(self, level: str) -> int:
        """Return number of log entries with the specified level."""
        return sum(1 for e in self._items if e.level == level)


class InMemoryMetricsStorage(InMemoryStorage[MetricSample]):
    """In-memory implementation of MetricsStoragePort.

    Stores metric samples in a list. Suitable for testing and
    low-volume applications where persistence is not required.

    Example:
        >>> import asyncio
        >>> from observabilipy import InMemoryMetricsStorage, MetricSample
        >>> async def demo():
        ...     storage = InMemoryMetricsStorage()
        ...     sample = MetricSample(name="test", timestamp=1.0, value=1.0, labels={})
        ...     await storage.write(sample)
        ...     return await storage.count()
        >>> asyncio.run(demo())
        1
    """

    @property
    def _samples(self) -> list[MetricSample]:
        """Alias for _items to maintain backward compatibility with tests."""
        return self._items

    async def read(self, since: float = 0) -> AsyncIterable[MetricSample]:
        """Read metric samples since the given timestamp.

        Returns samples with timestamp > since, ordered by timestamp ascending.
        """
        for sample in self._read_since(since):
            yield sample
