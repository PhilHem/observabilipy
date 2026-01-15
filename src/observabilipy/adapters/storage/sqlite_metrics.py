"""SQLite storage adapter for metrics."""

import json
import sqlite3
from collections.abc import AsyncIterable
from typing import Any

import aiosqlite

from observabilipy.adapters.storage.sqlite_base import (
    SQLiteStorageGeneric,
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
class SQLiteMetricsStorage(SQLiteStorageGeneric):
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

    _table_name = "metrics"
    _insert_query = _INSERT_METRIC
    _select_query = _SELECT_METRICS_SINCE
    _count_query = _COUNT_METRICS
    _delete_before_query = _DELETE_METRICS_BEFORE
    _clear_query = "DELETE FROM metrics"

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path, _METRICS_SCHEMA)

    def _to_row(self, item: MetricSample) -> tuple[Any, ...]:
        """Convert MetricSample to database row."""
        return (
            item.name,
            item.timestamp,
            item.value,
            json.dumps(item.labels),
        )

    def _from_row(self, row: sqlite3.Row | aiosqlite.Row) -> MetricSample:
        """Convert database row to MetricSample."""
        return MetricSample(
            name=row[0],
            timestamp=row[1],
            value=row[2],
            labels=_safe_json_loads(row[3]),
        )

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        await self._write(sample)

    async def read(self, since: float = 0) -> AsyncIterable[MetricSample]:
        """Read metric samples since the given timestamp.

        Returns samples with timestamp > since, ordered by timestamp ascending.
        """
        async for sample in self._read(since):
            yield sample

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        return await self._count()

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value."""
        return await self._delete_before(timestamp)

    # --- Sync methods using standard sqlite3 module ---

    def write_sync(self, sample: MetricSample) -> None:
        """Synchronous write for non-async contexts (testing, WSGI)."""
        self._write_sync(sample)

    def read_sync(self, since: float = 0) -> list[MetricSample]:
        """Synchronous read for non-async contexts (testing, WSGI)."""
        return self._read_sync(since)

    async def clear(self) -> None:
        """Clear all samples from storage."""
        await self._clear()

    def clear_sync(self) -> None:
        """Synchronous clear for non-async contexts (testing, WSGI)."""
        self._clear_sync()
