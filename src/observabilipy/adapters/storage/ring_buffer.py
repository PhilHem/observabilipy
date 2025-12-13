"""Ring buffer storage adapters for logs and metrics.

Provides bounded in-memory storage that automatically evicts oldest
entries when the buffer is full. Useful for production services that
need predictable memory usage.
"""

from collections import deque
from collections.abc import AsyncIterable

from observabilipy.core.exceptions import ConfigurationError
from observabilipy.core.models import LogEntry, MetricSample


class RingBufferLogStorage:
    """Ring buffer implementation of LogStoragePort.

    Stores log entries in a fixed-size circular buffer. When the buffer
    is full, the oldest entry is automatically evicted to make room for
    new entries.

    Args:
        max_size: Maximum number of entries to store.

    Example:
        >>> import asyncio
        >>> from observabilipy import RingBufferLogStorage, LogEntry
        >>> async def demo():
        ...     storage = RingBufferLogStorage(max_size=2)
        ...     for i in range(3):
        ...         entry = LogEntry(timestamp=float(i), level="INFO", message=f"m{i}")
        ...         await storage.write(entry)
        ...     return await storage.count()  # Only 2 kept due to max_size
        >>> asyncio.run(demo())
        2
    """

    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ConfigurationError(f"max_size must be positive, got {max_size}")
        self._buffer: deque[LogEntry] = deque(maxlen=max_size)

    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        self._buffer.append(entry)

    async def read(
        self, since: float = 0, level: str | None = None
    ) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp, optionally filtered by level.

        Returns entries with timestamp > since, ordered by timestamp ascending.
        If level is provided, only entries with matching level (case-insensitive)
        are returned.
        """
        filtered = [e for e in self._buffer if e.timestamp > since]
        if level is not None:
            level_upper = level.upper()
            filtered = [e for e in filtered if e.level.upper() == level_upper]
        for entry in sorted(filtered, key=lambda e: e.timestamp):
            yield entry

    async def count(self) -> int:
        """Return total number of log entries in storage."""
        return len(self._buffer)

    async def delete_before(self, timestamp: float) -> int:
        """Delete log entries with timestamp < given value."""
        original_count = len(self._buffer)
        # Rebuild deque with filtered entries, preserving maxlen
        filtered = [e for e in self._buffer if e.timestamp >= timestamp]
        self._buffer = deque(filtered, maxlen=self._buffer.maxlen)
        return original_count - len(self._buffer)

    async def delete_by_level_before(self, level: str, timestamp: float) -> int:
        """Delete log entries matching level with timestamp < given value."""
        original_count = len(self._buffer)
        filtered = [
            e
            for e in self._buffer
            if not (e.level == level and e.timestamp < timestamp)
        ]
        self._buffer = deque(filtered, maxlen=self._buffer.maxlen)
        return original_count - len(self._buffer)

    async def count_by_level(self, level: str) -> int:
        """Return number of log entries with the specified level."""
        return sum(1 for e in self._buffer if e.level == level)


class RingBufferMetricsStorage:
    """Ring buffer implementation of MetricsStoragePort.

    Stores metric samples in a fixed-size circular buffer. When the buffer
    is full, the oldest sample is automatically evicted to make room for
    new samples.

    Args:
        max_size: Maximum number of samples to store.

    Example:
        >>> import asyncio
        >>> from observabilipy import RingBufferMetricsStorage, MetricSample
        >>> async def demo():
        ...     storage = RingBufferMetricsStorage(max_size=2)
        ...     for i in range(3):
        ...         s = MetricSample(name="m", timestamp=float(i), value=float(i))
        ...         await storage.write(s)
        ...     return await storage.count()  # Only 2 kept due to max_size
        >>> asyncio.run(demo())
        2
    """

    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ConfigurationError(f"max_size must be positive, got {max_size}")
        self._buffer: deque[MetricSample] = deque(maxlen=max_size)

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        self._buffer.append(sample)

    async def read(self, since: float = 0) -> AsyncIterable[MetricSample]:
        """Read metric samples since the given timestamp.

        Returns samples with timestamp > since, ordered by timestamp ascending.
        """
        filtered = [s for s in self._buffer if s.timestamp > since]
        for sample in sorted(filtered, key=lambda s: s.timestamp):
            yield sample

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        return len(self._buffer)

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value."""
        original_count = len(self._buffer)
        # Rebuild deque with filtered samples, preserving maxlen
        filtered = [s for s in self._buffer if s.timestamp >= timestamp]
        self._buffer = deque(filtered, maxlen=self._buffer.maxlen)
        return original_count - len(self._buffer)
