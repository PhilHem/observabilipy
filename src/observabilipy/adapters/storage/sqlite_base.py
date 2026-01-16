"""Base class for SQLite storage adapters."""

import asyncio
import json
import sqlite3
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import aiosqlite


def _safe_json_loads(
    data: str, default: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Safely parse JSON data, returning default on decode error.

    Args:
        data: JSON string to parse.
        default: Value to return if parsing fails. Defaults to empty dict.

    Returns:
        Parsed JSON as dict, or default if parsing fails.
    """
    if default is None:
        default = {}
    try:
        result: dict[str, Any] = json.loads(data)
        return result
    except json.JSONDecodeError:
        return default


class AsyncConnectionManager:
    """Manages async (aiosqlite) database connections.

    Handles schema initialization and connection lifecycle for async contexts.
    For :memory: databases, maintains a persistent connection since SQLite
    in-memory databases are connection-scoped.
    """

    def __init__(self, db_path: str, schema: str) -> None:
        self._db_path = db_path
        self._schema = schema
        self._initialized = False
        self._init_lock: asyncio.Lock | None = None
        self._persistent_conn: aiosqlite.Connection | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the initialization lock (lazy to avoid event loop issues)."""
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()
        return self._init_lock

    @property
    def _should_close_connection(self) -> bool:
        """Return True if connections should be closed after use."""
        return self._db_path != ":memory:"

    async def _ensure_initialized(self) -> None:
        """Initialize database schema once."""
        if self._initialized:
            return
        async with self._get_lock():
            if self._initialized:
                return
            if self._db_path == ":memory:":
                self._persistent_conn = await aiosqlite.connect(":memory:")
                await self._persistent_conn.executescript(self._schema)
            else:
                async with aiosqlite.connect(self._db_path) as db:
                    await db.execute("PRAGMA journal_mode=WAL")
                    await db.executescript(self._schema)
            self._initialized = True

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection."""
        await self._ensure_initialized()
        if self._db_path == ":memory:":
            if self._persistent_conn is None:
                raise RuntimeError("Memory database connection not initialized")
            return self._persistent_conn
        return await aiosqlite.connect(self._db_path)

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager for async database connections.

        Automatically closes connections for file-based databases.
        For :memory: databases, keeps connections open (they're persistent).
        """
        db = await self._get_connection()
        try:
            yield db
        finally:
            if self._should_close_connection:
                await db.close()

    async def close(self) -> None:
        """Close persistent connection (for :memory: databases)."""
        if self._persistent_conn is not None:
            await self._persistent_conn.close()
            self._persistent_conn = None
            self._initialized = False


class SyncConnectionManager:
    """Manages sync (sqlite3) database connections.

    Handles schema initialization and connection lifecycle for sync contexts.
    For :memory: databases, maintains a persistent connection since SQLite
    in-memory databases are connection-scoped.

    IMPORTANT: For :memory: databases, this manager maintains a completely
    separate database instance from AsyncConnectionManager. This is intentional
    for thread-safety in concurrent scenarios.
    """

    def __init__(self, db_path: str, schema: str) -> None:
        self._db_path = db_path
        self._schema = schema
        self._initialized = False
        self._lock = threading.Lock()
        self._persistent_conn: sqlite3.Connection | None = None

    @property
    def _should_close_connection(self) -> bool:
        """Return True if connections should be closed after use."""
        return self._db_path != ":memory:"

    def _ensure_initialized(self) -> None:
        """Initialize database schema synchronously."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            if self._db_path == ":memory:":
                self._persistent_conn = sqlite3.connect(":memory:")
                self._persistent_conn.executescript(self._schema)
            else:
                with sqlite3.connect(self._db_path) as db:
                    db.execute("PRAGMA journal_mode=WAL")
                    db.executescript(self._schema)
            self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        """Get a sync database connection."""
        self._ensure_initialized()
        if self._db_path == ":memory:":
            if self._persistent_conn is None:
                raise RuntimeError("Sync memory database connection not initialized")
            return self._persistent_conn
        return sqlite3.connect(self._db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for sync database connections.

        Automatically closes connections for file-based databases.
        For :memory: databases, keeps connections open (they're persistent).
        """
        conn = self._get_connection()
        try:
            yield conn
        finally:
            if self._should_close_connection:
                conn.close()


class SQLiteStorageBase:
    """Base class for SQLite storage adapters.

    Delegates connection lifecycle to AsyncConnectionManager and SyncConnectionManager.
    Subclasses provide schema and implement domain-specific read/write methods.

    For :memory: databases, persistent connections are maintained since
    in-memory databases are connection-scoped in SQLite.

    IMPORTANT - :memory: Database Isolation:
    When using :memory: databases, the sync (sqlite3) and async (aiosqlite)
    connections are COMPLETELY SEPARATE and do NOT share data. This is because
    each manager maintains its own in-memory database instance. This is
    intentional and required for thread-safety in concurrent test scenarios.

    For testing, use fixtures that isolate sync and async operations.
    """

    def __init__(self, db_path: str, schema: str) -> None:
        self._db_path = db_path
        self._schema = schema
        self._async_manager = AsyncConnectionManager(db_path, schema)
        self._sync_manager = SyncConnectionManager(db_path, schema)

    async def close(self) -> None:
        """Close persistent connection (for :memory: databases)."""
        await self._async_manager.close()

    # --- Connection context managers (delegate to managers) ---

    @asynccontextmanager
    async def async_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager for async database connections."""
        async with self._async_manager.connection() as conn:
            yield conn

    @contextmanager
    def sync_connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for sync database connections."""
        with self._sync_manager.connection() as conn:
            yield conn


class SQLiteStorageGeneric(SQLiteStorageBase):
    """Generic SQLite storage with parameterized queries.

    Provides common CRUD operations for domain models. Subclasses configure
    schema, queries, table name, and row mapping functions.

    Type Parameters:
        T: The domain model type (e.g., LogEntry, MetricSample)
    """

    # Subclasses must define these class attributes
    _table_name: str
    _insert_query: str
    _select_query: str
    _count_query: str
    _delete_before_query: str
    _clear_query: str

    def _to_row(self, item: Any) -> tuple[Any, ...]:
        """Convert domain model to database row tuple.

        Must be overridden by subclasses.
        """
        raise NotImplementedError

    def _from_row(self, row: sqlite3.Row | aiosqlite.Row) -> Any:
        """Convert database row to domain model.

        Must be overridden by subclasses. Row can be either sqlite3.Row (sync)
        or aiosqlite.Row (async) - both support index-based access.
        """
        raise NotImplementedError

    async def _write(self, item: Any) -> None:
        """Write an item to storage."""
        async with self.async_connection() as db:
            await db.execute(self._insert_query, self._to_row(item))
            await db.commit()

    async def _read(self, since: float = 0) -> Any:
        """Read items since the given timestamp."""
        async with self.async_connection() as db:
            async with db.execute(self._select_query, (since,)) as cursor:
                async for row in cursor:
                    yield self._from_row(row)

    async def _count(self) -> int:
        """Return total number of items in storage."""
        async with self.async_connection() as db:
            async with db.execute(self._count_query) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def _delete_before(self, timestamp: float) -> int:
        """Delete items with timestamp < given value."""
        async with self.async_connection() as db:
            cursor = await db.execute(self._delete_before_query, (timestamp,))
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    async def _clear(self) -> None:
        """Clear all items from storage."""
        async with self.async_connection() as db:
            await db.execute(self._clear_query)
            await db.commit()

    async def clear(self) -> None:
        """Clear all items from storage."""
        await self._clear()

    # --- Sync methods ---

    def _write_sync(self, item: Any) -> None:
        """Synchronous write for non-async contexts."""
        with self.sync_connection() as conn:
            conn.execute(self._insert_query, self._to_row(item))
            conn.commit()

    def _read_sync(self, since: float = 0) -> list[Any]:
        """Synchronous read for non-async contexts."""
        with self.sync_connection() as conn:
            cursor = conn.execute(self._select_query, (since,))
            return [self._from_row(row) for row in cursor]

    def _clear_sync(self) -> None:
        """Synchronous clear for non-async contexts."""
        with self.sync_connection() as conn:
            conn.execute(self._clear_query)
            conn.commit()

    def clear_sync(self) -> None:
        """Synchronous clear for non-async contexts (testing, WSGI)."""
        self._clear_sync()
