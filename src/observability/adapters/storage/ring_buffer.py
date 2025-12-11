"""Ring buffer storage adapters for logs and metrics.

Provides bounded in-memory storage that automatically evicts oldest
entries when the buffer is full. Useful for production services that
need predictable memory usage.
"""

from collections import deque
from collections.abc import AsyncIterable

from observability.core.models import LogEntry, MetricSample


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
