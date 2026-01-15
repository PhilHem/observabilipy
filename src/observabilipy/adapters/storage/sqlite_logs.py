"""SQLite storage adapter for logs."""

import json
import sqlite3
from collections.abc import AsyncIterable
from typing import Any

import aiosqlite

from observabilipy.adapters.storage.sqlite_base import (
    SQLiteStorageGeneric,
    _safe_json_loads,
)
from observabilipy.core.models import LogEntry

_LOGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level_timestamp ON logs(level, timestamp);
"""

_INSERT_LOG = """
INSERT INTO logs (timestamp, level, message, attributes) VALUES (?, ?, ?, ?)
"""

_SELECT_LOGS = """
SELECT timestamp, level, message, attributes
FROM logs
WHERE timestamp > ?
ORDER BY timestamp ASC
"""

_SELECT_LOGS_BY_LEVEL = """
SELECT timestamp, level, message, attributes
FROM logs
WHERE timestamp > ? AND UPPER(level) = UPPER(?)
ORDER BY timestamp ASC
"""

_COUNT_LOGS = """
SELECT COUNT(*) FROM logs
"""

_DELETE_LOGS_BEFORE = """
DELETE FROM logs WHERE timestamp < ?
"""

_DELETE_LOGS_BY_LEVEL_BEFORE = """
DELETE FROM logs WHERE level = ? AND timestamp < ?
"""

_COUNT_LOGS_BY_LEVEL = """
SELECT COUNT(*) FROM logs WHERE level = ?
"""


# @tra: Adapter.SQLiteStorage.ImplementsLogStoragePort
class SQLiteLogStorage(SQLiteStorageGeneric):
    """SQLite implementation of LogStoragePort.

    Stores log entries in a SQLite database using aiosqlite for
    non-blocking async operations. Uses WAL mode for concurrent access.

    For :memory: databases, a persistent connection is maintained since
    in-memory databases are connection-scoped in SQLite.

    Sync methods (write_sync, read_sync, clear_sync) use the standard
    sqlite3 module for non-async contexts like WSGI or testing.
    For file-based databases, sync and async methods share the same file.
    For :memory: databases, sync and async have separate in-memory DBs.
    """

    _table_name = "logs"
    _insert_query = _INSERT_LOG
    _select_query = _SELECT_LOGS
    _count_query = _COUNT_LOGS
    _delete_before_query = _DELETE_LOGS_BEFORE
    _clear_query = "DELETE FROM logs"

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path, _LOGS_SCHEMA)

    def _to_row(self, item: LogEntry) -> tuple[Any, ...]:
        """Convert LogEntry to database row."""
        return (
            item.timestamp,
            item.level,
            item.message,
            json.dumps(item.attributes),
        )

    def _from_row(self, row: sqlite3.Row | aiosqlite.Row) -> LogEntry:
        """Convert database row to LogEntry."""
        return LogEntry(
            timestamp=row[0],
            level=row[1],
            message=row[2],
            attributes=_safe_json_loads(row[3]),
        )

    # @tra: Adapter.SQLiteStorage.PersistsAcrossInstances
    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        await self._write(entry)

    # @tra: Adapter.SQLiteStorage.LevelFiltering
    async def read(
        self, since: float = 0, level: str | None = None
    ) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp, optionally filtered by level.

        If level is provided, only entries with matching level (case-insensitive)
        are returned.
        """
        if level is not None:
            # Use level-specific query
            async with self.async_connection() as db:
                params: tuple[float, str] = (since, level)
                async with db.execute(_SELECT_LOGS_BY_LEVEL, params) as cursor:
                    async for row in cursor:
                        yield self._from_row(row)
        else:
            # Use base class implementation
            async for entry in self._read(since):
                yield entry

    async def count(self) -> int:
        """Return total number of log entries in storage."""
        return await self._count()

    async def delete_before(self, timestamp: float) -> int:
        """Delete log entries with timestamp < given value."""
        return await self._delete_before(timestamp)

    # @tra: Adapter.SQLiteStorage.LevelFiltering
    async def delete_by_level_before(self, level: str, timestamp: float) -> int:
        """Delete log entries matching level with timestamp < given value."""
        async with self.async_connection() as db:
            cursor = await db.execute(_DELETE_LOGS_BY_LEVEL_BEFORE, (level, timestamp))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    # @tra: Adapter.SQLiteStorage.LevelFiltering
    async def count_by_level(self, level: str) -> int:
        """Return number of log entries with the specified level."""
        async with self.async_connection() as db:
            async with db.execute(_COUNT_LOGS_BY_LEVEL, (level,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    # --- Sync methods using standard sqlite3 module ---

    def write_sync(self, entry: LogEntry) -> None:
        """Synchronous write for non-async contexts (testing, WSGI)."""
        self._write_sync(entry)

    def read_sync(self, since: float = 0, level: str | None = None) -> list[LogEntry]:
        """Synchronous read for non-async contexts (testing, WSGI)."""
        if level is not None:
            # Use level-specific query
            with self.sync_connection() as conn:
                params: tuple[float, str] = (since, level)
                cursor = conn.execute(_SELECT_LOGS_BY_LEVEL, params)
                return [self._from_row(row) for row in cursor]
        else:
            return self._read_sync(since)
