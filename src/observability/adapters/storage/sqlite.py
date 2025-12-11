"""SQLite storage adapters for logs and metrics."""

import json
from collections.abc import AsyncIterable

import aiosqlite

from observability.core.models import LogEntry, MetricSample

_LOGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
"""

_METRICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    timestamp REAL NOT NULL,
    value REAL NOT NULL,
    labels TEXT NOT NULL DEFAULT '{}'
);
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

_INSERT_METRIC = """
INSERT INTO metrics (name, timestamp, value, labels) VALUES (?, ?, ?, ?)
"""

_SELECT_METRICS = """
SELECT name, timestamp, value, labels FROM metrics
"""


class SQLiteLogStorage:
    """SQLite implementation of LogStoragePort.

    Stores log entries in a SQLite database using aiosqlite for
    non-blocking async operations.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection, creating tables if needed."""
        db = await aiosqlite.connect(self._db_path)
        await db.executescript(_LOGS_SCHEMA)
        return db

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
            await db.close()

    async def read(self, since: float = 0) -> AsyncIterable[LogEntry]:
        """Read log entries since the given timestamp."""
        db = await self._get_connection()
        try:
            async with db.execute(_SELECT_LOGS, (since,)) as cursor:
                async for row in cursor:
                    yield LogEntry(
                        timestamp=row[0],
                        level=row[1],
                        message=row[2],
                        attributes=json.loads(row[3]),
                    )
        finally:
            await db.close()


class SQLiteMetricsStorage:
    """SQLite implementation of MetricsStoragePort.

    Stores metric samples in a SQLite database using aiosqlite for
    non-blocking async operations.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection, creating tables if needed."""
        db = await aiosqlite.connect(self._db_path)
        await db.executescript(_METRICS_SCHEMA)
        return db

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
            await db.close()

    async def scrape(self) -> AsyncIterable[MetricSample]:
        """Scrape all current metric samples."""
        db = await self._get_connection()
        try:
            async with db.execute(_SELECT_METRICS) as cursor:
                async for row in cursor:
                    yield MetricSample(
                        name=row[0],
                        timestamp=row[1],
                        value=row[2],
                        labels=json.loads(row[3]),
                    )
        finally:
            await db.close()
