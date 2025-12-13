"""In-memory storage adapters for logs and metrics."""

from collections.abc import AsyncIterable

from observabilipy.core.models import LogEntry, MetricSample


class InMemoryLogStorage:
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

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []

    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        self._entries.append(entry)

    async def read(
        self, since: float = 0, level: str | None = None
    ) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp, optionally filtered by level.

        Returns entries with timestamp > since, ordered by timestamp ascending.
        If level is provided, only entries with matching level (case-insensitive)
        are returned.
        """
        filtered = [e for e in self._entries if e.timestamp > since]
        if level is not None:
            level_upper = level.upper()
            filtered = [e for e in filtered if e.level.upper() == level_upper]
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

    async def delete_by_level_before(self, level: str, timestamp: float) -> int:
        """Delete log entries matching level with timestamp < given value."""
        original_count = len(self._entries)
        self._entries = [
            e
            for e in self._entries
            if not (e.level == level and e.timestamp < timestamp)
        ]
        return original_count - len(self._entries)

    async def count_by_level(self, level: str) -> int:
        """Return number of log entries with the specified level."""
        return sum(1 for e in self._entries if e.level == level)


class InMemoryMetricsStorage:
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

    def __init__(self) -> None:
        self._samples: list[MetricSample] = []

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        self._samples.append(sample)

    async def read(self, since: float = 0) -> AsyncIterable[MetricSample]:
        """Read metric samples since the given timestamp.

        Returns samples with timestamp > since, ordered by timestamp ascending.
        """
        filtered = [s for s in self._samples if s.timestamp > since]
        for sample in sorted(filtered, key=lambda s: s.timestamp):
            yield sample

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        return len(self._samples)

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value."""
        original_count = len(self._samples)
        self._samples = [s for s in self._samples if s.timestamp >= timestamp]
        return original_count - len(self._samples)
