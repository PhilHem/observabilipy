"""Domain services for log and metric operations.

Services wrap storage ports to add domain logic like filtering,
keeping adapters thin and focusing domain rules in the core layer.
"""

from collections.abc import AsyncIterable

from observabilipy.core.models import LogEntry
from observabilipy.core.ports import LogStoragePort


# @tra: Core.LogStorageWithLevelFilter.DomainFiltering
class LogStorageWithLevelFilter:
    """Domain service wrapper adding level-based filtering to any LogStoragePort.

    Extracts level filtering logic from storage adapters into the domain layer.
    The wrapper delegates basic operations to the underlying storage while
    providing pure domain logic for level-based filtering.

    This keeps storage adapters thin (they just persist/retrieve) while
    centralizing filtering rules in the core domain.

    Example:
        >>> import asyncio
        >>> from observabilipy import InMemoryLogStorage, LogEntry
        >>> from observabilipy.core.services import LogStorageWithLevelFilter
        >>> async def demo():
        ...     storage = InMemoryLogStorage()
        ...     wrapper = LogStorageWithLevelFilter(storage)
        ...     entry1 = LogEntry(timestamp=1.0, level="ERROR", message="e")
        ...     entry2 = LogEntry(timestamp=2.0, level="INFO", message="i")
        ...     await wrapper.write(entry1)
        ...     await wrapper.write(entry2)
        ...     errors = [e async for e in wrapper.filter_by_level("ERROR")]
        ...     return len(errors)
        >>> asyncio.run(demo())
        1
    """

    def __init__(self, storage: LogStoragePort) -> None:
        """Initialize wrapper with underlying storage.

        Args:
            storage: Any LogStoragePort implementation to wrap.
        """
        self._storage = storage

    # --- Domain filtering methods (the reason this service exists) ---

    async def filter_by_level(
        self, level: str, since: float = 0
    ) -> AsyncIterable[LogEntry]:
        """Read log entries filtered by level.

        Args:
            level: Log level to filter by (case-insensitive).
            since: Unix timestamp. Returns entries with timestamp > since.

        Yields:
            LogEntry objects matching the level, ordered by timestamp ascending.
        """
        level_upper = level.upper()
        async for entry in self._storage.read(since=since):
            if entry.level.upper() == level_upper:
                yield entry

    async def count_by_level(self, level: str) -> int:
        """Return number of log entries with the specified level.

        Args:
            level: Log level to count (e.g., "ERROR", "INFO").

        Returns:
            Number of entries with this level.
        """
        count = 0
        async for entry in self._storage.read():
            if entry.level == level:
                count += 1
        return count

    async def delete_by_level_before(self, level: str, timestamp: float) -> int:
        """Delete log entries matching level with timestamp < given value.

        Note: This implementation reads all entries, filters, and rewrites.
        For storage backends with native level-indexed deletion (like SQLite),
        you may want to call the underlying storage method directly for
        better performance.

        Args:
            level: Log level to match (e.g., "ERROR", "INFO").
            timestamp: Unix timestamp. Entries with this level and
                      timestamp < this value will be deleted.

        Returns:
            Number of entries deleted.
        """
        # Delegate to underlying storage if it has native support
        if hasattr(self._storage, "delete_by_level_before"):
            return await self._storage.delete_by_level_before(level, timestamp)
        # Fallback: read all, filter, clear, rewrite (inefficient but correct)
        entries_to_keep: list[LogEntry] = []
        deleted = 0
        async for entry in self._storage.read():
            if entry.level == level and entry.timestamp < timestamp:
                deleted += 1
            else:
                entries_to_keep.append(entry)
        await self._storage.clear()
        for entry in entries_to_keep:
            await self._storage.write(entry)
        return deleted

    # --- Pass-through methods delegating to underlying storage ---

    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        await self._storage.write(entry)

    def write_sync(self, entry: LogEntry) -> None:
        """Synchronous write for non-async contexts (testing, WSGI)."""
        self._storage.write_sync(entry)

    async def read(
        self, since: float = 0, level: str | None = None
    ) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp, optionally filtered by level.

        Args:
            since: Unix timestamp. Returns entries with timestamp > since.
            level: Optional log level filter (case-insensitive).

        Yields:
            LogEntry objects, ordered by timestamp ascending.
        """
        if level is not None:
            async for entry in self.filter_by_level(level, since):
                yield entry
        else:
            async for entry in self._storage.read(since=since):
                yield entry

    async def count(self) -> int:
        """Return total number of log entries in storage."""
        return await self._storage.count()

    async def delete_before(self, timestamp: float) -> int:
        """Delete log entries with timestamp < given value."""
        return await self._storage.delete_before(timestamp)

    async def clear(self) -> None:
        """Clear all entries from storage."""
        await self._storage.clear()

    def clear_sync(self) -> None:
        """Synchronous clear for non-async contexts (testing, WSGI)."""
        self._storage.clear_sync()
