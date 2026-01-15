"""SQLite storage adapter for logs."""

import json
from collections.abc import AsyncIterable

from observabilipy.adapters.storage.sqlite_base import SQLiteStorageBase
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
class SQLiteLogStorage(SQLiteStorageBase):
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

    def __init__(self, db_path: str) -> None:
        super().__init__(db_path, _LOGS_SCHEMA)

    # @tra: Adapter.SQLiteStorage.PersistsAcrossInstances
    async def write(self, entry: LogEntry) -> None:
        """Write a log entry to storage."""
        db = await self._get_connection()
        try:
            await db.execute(
                _INSERT_LOG,
                (
                    entry.timestamp,
                    entry.level,
                    entry.message,
                    json.dumps(entry.attributes),
                ),
            )
            await db.commit()
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def read(
        self, since: float = 0, level: str | None = None
    ) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp, optionally filtered by level.

        If level is provided, only entries with matching level (case-insensitive)
        are returned.
        """
        db = await self._get_connection()
        try:
            if level is not None:
                query = _SELECT_LOGS_BY_LEVEL
                params: tuple[float] | tuple[float, str] = (since, level)
            else:
                query = _SELECT_LOGS
                params = (since,)
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    yield LogEntry(
                        timestamp=row[0],
                        level=row[1],
                        message=row[2],
                        attributes=json.loads(row[3]),
                    )
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def count(self) -> int:
        """Return total number of log entries in storage."""
        db = await self._get_connection()
        try:
            async with db.execute(_COUNT_LOGS) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def delete_before(self, timestamp: float) -> int:
        """Delete log entries with timestamp < given value."""
        db = await self._get_connection()
        try:
            cursor = await db.execute(_DELETE_LOGS_BEFORE, (timestamp,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def delete_by_level_before(self, level: str, timestamp: float) -> int:
        """Delete log entries matching level with timestamp < given value."""
        db = await self._get_connection()
        try:
            cursor = await db.execute(_DELETE_LOGS_BY_LEVEL_BEFORE, (level, timestamp))
            deleted = cursor.rowcount
            await db.commit()
            return deleted
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def count_by_level(self, level: str) -> int:
        """Return number of log entries with the specified level."""
        db = await self._get_connection()
        try:
            async with db.execute(_COUNT_LOGS_BY_LEVEL, (level,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        finally:
            if self._db_path != ":memory:":
                await db.close()

    # --- Sync methods using standard sqlite3 module ---

    def write_sync(self, entry: LogEntry) -> None:
        """Synchronous write for non-async contexts (testing, WSGI)."""
        conn = self._get_sync_connection()
        try:
            conn.execute(
                _INSERT_LOG,
                (
                    entry.timestamp,
                    entry.level,
                    entry.message,
                    json.dumps(entry.attributes),
                ),
            )
            conn.commit()
        finally:
            if self._db_path != ":memory:":
                conn.close()

    def read_sync(self, since: float = 0, level: str | None = None) -> list[LogEntry]:
        """Synchronous read for non-async contexts (testing, WSGI)."""
        conn = self._get_sync_connection()
        try:
            if level is not None:
                query = _SELECT_LOGS_BY_LEVEL
                params: tuple[float] | tuple[float, str] = (since, level)
            else:
                query = _SELECT_LOGS
                params = (since,)
            cursor = conn.execute(query, params)
            return [
                LogEntry(
                    timestamp=row[0],
                    level=row[1],
                    message=row[2],
                    attributes=json.loads(row[3]),
                )
                for row in cursor
            ]
        finally:
            if self._db_path != ":memory:":
                conn.close()

    async def clear(self) -> None:
        """Clear all entries from storage."""
        db = await self._get_connection()
        try:
            await db.execute("DELETE FROM logs")
            await db.commit()
        finally:
            if self._db_path != ":memory:":
                await db.close()

    def clear_sync(self) -> None:
        """Synchronous clear for non-async contexts (testing, WSGI)."""
        conn = self._get_sync_connection()
        try:
            conn.execute("DELETE FROM logs")
            conn.commit()
        finally:
            if self._db_path != ":memory:":
                conn.close()
