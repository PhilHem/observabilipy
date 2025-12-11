"""Port interfaces for storage adapters.

These protocols define the contracts that storage adapters must implement.
The core domain depends only on these interfaces, not concrete implementations.
"""

from collections.abc import AsyncIterable
from typing import Protocol, runtime_checkable

from observabilipy.core.models import LogEntry, MetricSample


@runtime_checkable
class LogStoragePort(Protocol):
    """Port for log storage operations.

    Adapters implementing this protocol can store and retrieve log entries.
    Examples: InMemoryLogStorage, SQLiteLogStorage, RingBufferLogStorage.
    """

    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        ...

    def read(self, since: float = 0) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp.

        Args:
            since: Unix timestamp. Returns entries with timestamp > since.
                   Default 0 returns all entries.

        Returns:
            AsyncIterable of LogEntry objects, ordered by timestamp ascending.
        """
        ...

    async def count(self) -> int:
        """Return total number of log entries in storage."""
        ...

    async def delete_before(self, timestamp: float) -> int:
        """Delete log entries with timestamp < given value.

        Args:
            timestamp: Unix timestamp. Entries with timestamp < this value
                       will be deleted.

        Returns:
            Number of entries deleted.
        """
        ...


@runtime_checkable
class MetricsStoragePort(Protocol):
    """Port for metrics storage operations.

    Adapters implementing this protocol can store and retrieve metric samples.
    Examples: InMemoryMetricsStorage, SQLiteMetricsStorage.
    """

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        ...

    def scrape(self) -> AsyncIterable[MetricSample]:
        """Scrape all current metric samples.

        Returns:
            AsyncIterable of MetricSample objects representing current state.
        """
        ...

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        ...

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value.

        Args:
            timestamp: Unix timestamp. Samples with timestamp < this value
                       will be deleted.

        Returns:
            Number of samples deleted.
        """
        ...
