"""Port interfaces for storage adapters.

These protocols define the contracts that storage adapters must implement.
The core domain depends only on these interfaces, not concrete implementations.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from observability.core.models import LogEntry, MetricSample


@runtime_checkable
class LogStoragePort(Protocol):
    """Port for log storage operations.

    Adapters implementing this protocol can store and retrieve log entries.
    Examples: InMemoryLogStorage, SQLiteLogStorage, RingBufferLogStorage.
    """

    def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        ...

    def read(self, since: float = 0) -> Iterable[LogEntry]:
        """Read log entries since the given timestamp.

        Args:
            since: Unix timestamp. Returns entries with timestamp > since.
                   Default 0 returns all entries.

        Returns:
            Iterable of LogEntry objects, ordered by timestamp ascending.
        """
        ...


@runtime_checkable
class MetricsStoragePort(Protocol):
    """Port for metrics storage operations.

    Adapters implementing this protocol can store and retrieve metric samples.
    Examples: InMemoryMetricsStorage, SQLiteMetricsStorage.
    """

    def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        ...

    def scrape(self) -> Iterable[MetricSample]:
        """Scrape all current metric samples.

        Returns:
            Iterable of MetricSample objects representing current state.
        """
        ...
