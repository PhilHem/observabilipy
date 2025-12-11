"""Ring buffer storage adapters for logs and metrics.

Provides bounded in-memory storage that automatically evicts oldest
entries when the buffer is full. Useful for production services that
need predictable memory usage.
"""

from collections import deque
from collections.abc import AsyncIterable

from observabilipy.core.models import LogEntry, MetricSample


class RingBufferLogStorage:
    """Ring buffer implementation of LogStoragePort.

    Stores log entries in a fixed-size circular buffer. When the buffer
    is full, the oldest entry is automatically evicted to make room for
    new entries.

    Args:
        max_size: Maximum number of entries to store.
    """

    def __init__(self, max_size: int) -> None:
        self._buffer: deque[LogEntry] = deque(maxlen=max_size)

    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        self._buffer.append(entry)

    async def read(self, since: float = 0) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp.

        Returns entries with timestamp > since, ordered by timestamp ascending.
        """
        filtered = [e for e in self._buffer if e.timestamp > since]
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


class RingBufferMetricsStorage:
    """Ring buffer implementation of MetricsStoragePort.

    Stores metric samples in a fixed-size circular buffer. When the buffer
    is full, the oldest sample is automatically evicted to make room for
    new samples.

    Args:
        max_size: Maximum number of samples to store.
    """

    def __init__(self, max_size: int) -> None:
        self._buffer: deque[MetricSample] = deque(maxlen=max_size)

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        self._buffer.append(sample)

    async def scrape(self) -> AsyncIterable[MetricSample]:
        """Scrape all current metric samples."""
        for sample in self._buffer:
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
