"""SQLite storage adapter for metrics."""

import asyncio
import json
import sqlite3
import threading
from collections.abc import AsyncIterable

import aiosqlite

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
class SQLiteMetricsStorage:
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
        self._db_path = db_path
        self._initialized = False
        self._init_lock: asyncio.Lock | None = None
        self._persistent_conn: aiosqlite.Connection | None = None
        # Sync state (uses standard sqlite3 module)
        self._sync_initialized = False
        self._sync_lock = threading.Lock()
        self._sync_conn: sqlite3.Connection | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the initialization lock (lazy to avoid event loop issues)."""
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()
        return self._init_lock

    async def _ensure_initialized(self) -> None:
        """Initialize database schema once."""
        if self._initialized:
            return
        async with self._get_lock():
            if self._initialized:
                return
            if self._db_path == ":memory:":
                # For :memory: DBs, keep a persistent connection
                self._persistent_conn = await aiosqlite.connect(":memory:")
                await self._persistent_conn.executescript(_METRICS_SCHEMA)
            else:
                async with aiosqlite.connect(self._db_path) as db:
                    await db.execute("PRAGMA journal_mode=WAL")
                    await db.executescript(_METRICS_SCHEMA)
            self._initialized = True

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection."""
        await self._ensure_initialized()
        if self._db_path == ":memory:":
            assert self._persistent_conn is not None
            return self._persistent_conn
        return await aiosqlite.connect(self._db_path)

    async def write(self, sample: MetricSample) -> None:
        """Write a metric sample to storage."""
        db = await self._get_connection()
        try:
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
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def read(self, since: float = 0) -> AsyncIterable[MetricSample]:
        """Read metric samples since the given timestamp.

        Returns samples with timestamp > since, ordered by timestamp ascending.
        """
        db = await self._get_connection()
        try:
            async with db.execute(_SELECT_METRICS_SINCE, (since,)) as cursor:
                async for row in cursor:
                    yield MetricSample(
                        name=row[0],
                        timestamp=row[1],
                        value=row[2],
                        labels=json.loads(row[3]),
                    )
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def count(self) -> int:
        """Return total number of metric samples in storage."""
        db = await self._get_connection()
        try:
            async with db.execute(_COUNT_METRICS) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def delete_before(self, timestamp: float) -> int:
        """Delete metric samples with timestamp < given value."""
        db = await self._get_connection()
        try:
            cursor = await db.execute(_DELETE_METRICS_BEFORE, (timestamp,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted
        finally:
            if self._db_path != ":memory:":
                await db.close()

    async def close(self) -> None:
        """Close persistent connection (for :memory: databases)."""
        if self._persistent_conn is not None:
            await self._persistent_conn.close()
            self._persistent_conn = None
            self._initialized = False

    # --- Sync methods using standard sqlite3 module ---

    def _ensure_initialized_sync(self) -> None:
        """Initialize database schema synchronously."""
        if self._sync_initialized:
            return
        with self._sync_lock:
            if self._sync_initialized:
                return
            if self._db_path == ":memory:":
                # For :memory: DBs, keep a persistent connection (separate from async)
                self._sync_conn = sqlite3.connect(":memory:")
                self._sync_conn.executescript(_METRICS_SCHEMA)
            else:
                with sqlite3.connect(self._db_path) as db:
                    db.execute("PRAGMA journal_mode=WAL")
                    db.executescript(_METRICS_SCHEMA)
            self._sync_initialized = True

    def _get_sync_connection(self) -> sqlite3.Connection:
        """Get a sync database connection."""
        self._ensure_initialized_sync()
        if self._db_path == ":memory:":
            assert self._sync_conn is not None
            return self._sync_conn
        return sqlite3.connect(self._db_path)

    def write_sync(self, sample: MetricSample) -> None:
        """Synchronous write for non-async contexts (testing, WSGI)."""
        conn = self._get_sync_connection()
        try:
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
        finally:
            if self._db_path != ":memory:":
                conn.close()

    def read_sync(self, since: float = 0) -> list[MetricSample]:
        """Synchronous read for non-async contexts (testing, WSGI)."""
        conn = self._get_sync_connection()
        try:
            cursor = conn.execute(_SELECT_METRICS_SINCE, (since,))
            return [
                MetricSample(
                    name=row[0],
                    timestamp=row[1],
                    value=row[2],
                    labels=json.loads(row[3]),
                )
                for row in cursor
            ]
        finally:
            if self._db_path != ":memory:":
                conn.close()

    async def clear(self) -> None:
        """Clear all samples from storage."""
        db = await self._get_connection()
        try:
            await db.execute("DELETE FROM metrics")
            await db.commit()
        finally:
            if self._db_path != ":memory:":
                await db.close()

    def clear_sync(self) -> None:
        """Synchronous clear for non-async contexts (testing, WSGI)."""
        conn = self._get_sync_connection()
        try:
            conn.execute("DELETE FROM metrics")
            conn.commit()
        finally:
            if self._db_path != ":memory:":
                conn.close()
