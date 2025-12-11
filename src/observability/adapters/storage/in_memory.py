"""In-memory storage adapters for logs and metrics."""

from collections.abc import AsyncIterable

from observability.core.models import LogEntry, MetricSample


class InMemoryLogStorage:
    """In-memory implementation of LogStoragePort.

    Stores log entries in a list. Suitable for testing and
    low-volume applications where persistence is not required.
    """

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []

    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        self._entries.append(entry)

    async def read(self, since: float = 0) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp.

        Returns entries with timestamp > since, ordered by timestamp ascending.
        """
        filtered = [e for e in self._entries if e.timestamp > since]
        for entry in sorted(filtered, key=lambda e: e.timestamp):
            yield entry

    async def count(self) -> int:
        """Return total number of log entries in storage."""
        return len(self._entries)

    async def delete_before(self, timestamp: float) -> int:
        """Delete log entries with timestamp < given value."""
        original_count = len(self._entries)
        self._entries = [e for e in self._entries if e.timestamp >= timestamp]
        return original_count - len(self._entries)


class InMemoryMetricsStorage:
    """In-memory implementation of MetricsStoragePort.

    Stores metric samples in a list. Suitable for testing and
    low-volume applications where persistence is not required.
    """

    def __init__(self) -> None:
        self._samples: list[MetricSample] = []

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        self._samples.append(sample)

    async def scrape(self) -> AsyncIterable[MetricSample]:
        """Scrape all current metric samples."""
        for sample in self._samples:
            yield sample

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        return len(self._samples)

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value."""
        original_count = len(self._samples)
        self._samples = [s for s in self._samples if s.timestamp >= timestamp]
        return original_count - len(self._samples)
