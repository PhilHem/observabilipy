"""In-memory storage adapters for logs and metrics."""

from collections.abc import Iterable

from observability.core.models import LogEntry, MetricSample


class InMemoryLogStorage:
    """In-memory implementation of LogStoragePort.

    Stores log entries in a list. Suitable for testing and
    low-volume applications where persistence is not required.
    """

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []

    def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        self._entries.append(entry)

    def read(self, since: float = 0) -> Iterable[LogEntry]:
        """Read log entries since the given timestamp.

        Returns entries with timestamp > since, ordered by timestamp ascending.
        """
        filtered = [e for e in self._entries if e.timestamp > since]
        return sorted(filtered, key=lambda e: e.timestamp)


class InMemoryMetricsStorage:
    """In-memory implementation of MetricsStoragePort.

    Stores metric samples in a list. Suitable for testing and
    low-volume applications where persistence is not required.
    """

    def __init__(self) -> None:
        self._samples: list[MetricSample] = []

    def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        self._samples.append(sample)

    def scrape(self) -> Iterable[MetricSample]:
        """Scrape all current metric samples."""
        return list(self._samples)
