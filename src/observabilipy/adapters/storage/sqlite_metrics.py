"""SQLite storage adapter for metrics."""

import json
from collections.abc import AsyncIterable

from observabilipy.adapters.storage.sqlite_base import (
    SQLiteStorageBase,
    _safe_json_loads,
)
from observabilipy.core.models import MetricSample

_METRICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    timestamp REAL NOT NULL,
    value REAL NOT NULL,
    labels TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
"""

_INSERT_METRIC = """
INSERT INTO metrics (name, timestamp, value, labels) VALUES (?, ?, ?, ?)
"""

_SELECT_METRICS_SINCE = """
SELECT name, timestamp, value, labels FROM metrics
WHERE timestamp > ?
ORDER BY timestamp ASC
"""

_COUNT_METRICS = """
SELECT COUNT(*) FROM metrics
"""

_DELETE_METRICS_BEFORE = """
DELETE FROM metrics WHERE timestamp < ?
"""


# @tra: Adapter.SQLiteStorage.ImplementsMetricsStoragePort
# @tra: Adapter.SQLiteStorage.PersistsAcrossInstances
class SQLiteMetricsStorage(SQLiteStorageBase):
    """SQLite implementation of MetricsStoragePort.

    Stores metric samples in a SQLite database using aiosqlite for
    non-blocking async operations. Uses WAL mode for concurrent access.

    For :memory: databases, a persistent connection is maintained since
    in-memory databases are connection-scoped in SQLite.

    Sync methods (write_sync, read_sync, clear_sync) use the standard
    sqlite3 module for non-async contexts like WSGI or testing.
    For file-based databases, sync and async methods share the same file.
    For :memory: databases, sync and async have separate in-memory DBs.
    """

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path, _METRICS_SCHEMA)

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        async with self.async_connection() as db:
            await db.execute(
                _INSERT_METRIC,
                (
                    sample.name,
                    sample.timestamp,
                    sample.value,
                    json.dumps(sample.labels),
                ),
            )
            await db.commit()

    async def read(self, since: float = 0) -> AsyncIterable[MetricSample]:
        """Read metric samples since the given timestamp.

        Returns samples with timestamp > since, ordered by timestamp ascending.
        """
        async with self.async_connection() as db:
            async with db.execute(_SELECT_METRICS_SINCE, (since,)) as cursor:
                async for row in cursor:
                    yield MetricSample(
                        name=row[0],
                        timestamp=row[1],
                        value=row[2],
                        labels=_safe_json_loads(row[3]),
                    )

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        async with self.async_connection() as db:
            async with db.execute(_COUNT_METRICS) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value."""
        async with self.async_connection() as db:
            cursor = await db.execute(_DELETE_METRICS_BEFORE, (timestamp,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    # --- Sync methods using standard sqlite3 module ---

    def write_sync(self, sample: MetricSample) -> None:
        """Synchronous write for non-async contexts (testing, WSGI)."""
        with self.sync_connection() as conn:
            conn.execute(
                _INSERT_METRIC,
                (
                    sample.name,
                    sample.timestamp,
                    sample.value,
                    json.dumps(sample.labels),
                ),
            )
            conn.commit()

    def read_sync(self, since: float = 0) -> list[MetricSample]:
        """Synchronous read for non-async contexts (testing, WSGI)."""
        with self.sync_connection() as conn:
            cursor = conn.execute(_SELECT_METRICS_SINCE, (since,))
            samples = []
            for row in cursor:
                samples.append(
                    MetricSample(
                        name=row[0],
                        timestamp=row[1],
                        value=row[2],
                        labels=_safe_json_loads(row[3]),
                    )
                )
            return samples

    async def clear(self) -> None:
        """Clear all samples from storage."""
        async with self.async_connection() as db:
            await db.execute("DELETE FROM metrics")
            await db.commit()

    def clear_sync(self) -> None:
        """Synchronous clear for non-async contexts (testing, WSGI)."""
        with self.sync_connection() as conn:
            conn.execute("DELETE FROM metrics")
            conn.commit()
