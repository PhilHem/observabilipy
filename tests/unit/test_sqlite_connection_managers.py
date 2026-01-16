"""Tests for SQLite connection manager classes.

These tests verify that the async and sync connection managers
properly initialize the schema and maintain independent connections
for :memory: databases.
"""

import pytest

from observabilipy.adapters.storage.sqlite_base import (
    AsyncConnectionManager,
    SyncConnectionManager,
)

pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.tra("Adapter.SQLiteStorage.ConnectionManager"),
]

# Schema for testing - creates a simple test table
TEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS test_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
"""


class TestAsyncConnectionManager:
    """Tests for AsyncConnectionManager."""

    @pytest.mark.storage
    async def test_async_connection_manager_initializes_schema(self) -> None:
        """AsyncConnectionManager creates schema on first connection."""
        manager = AsyncConnectionManager(":memory:", TEST_SCHEMA)

        try:
            async with manager.connection() as conn:
                # Insert a row to verify schema was created
                await conn.execute(
                    "INSERT INTO test_items (name) VALUES (?)", ("test",)
                )
                await conn.commit()
                cursor = await conn.execute("SELECT COUNT(*) FROM test_items")
                row = await cursor.fetchone()
                assert row[0] == 1
        finally:
            await manager.close()


class TestSyncConnectionManager:
    """Tests for SyncConnectionManager."""

    @pytest.mark.storage
    def test_sync_connection_manager_initializes_schema(self) -> None:
        """SyncConnectionManager creates schema on first connection."""
        manager = SyncConnectionManager(":memory:", TEST_SCHEMA)

        with manager.connection() as conn:
            # Insert a row to verify schema was created
            conn.execute("INSERT INTO test_items (name) VALUES (?)", ("test",))
            conn.commit()
            cursor = conn.execute("SELECT COUNT(*) FROM test_items")
            row = cursor.fetchone()
            assert row[0] == 1


class TestConnectionManagerIndependence:
    """Tests verifying sync and async managers are independent for :memory: DBs."""

    @pytest.mark.storage
    async def test_connection_managers_are_independent_for_memory_db(self) -> None:
        """Sync and async managers have separate in-memory databases.

        This test verifies the intentional isolation between sync (sqlite3)
        and async (aiosqlite) connections for :memory: databases. Each manager
        maintains its own in-memory database instance - data written through
        one manager should NOT be visible through the other.
        """
        async_manager = AsyncConnectionManager(":memory:", TEST_SCHEMA)
        sync_manager = SyncConnectionManager(":memory:", TEST_SCHEMA)

        try:
            # Write through async manager
            async with async_manager.connection() as conn:
                await conn.execute(
                    "INSERT INTO test_items (name) VALUES (?)", ("async_item",)
                )
                await conn.commit()

            # Write through sync manager
            with sync_manager.connection() as conn:
                conn.execute("INSERT INTO test_items (name) VALUES (?)", ("sync_item",))
                conn.commit()

            # Verify async manager only sees async data
            async with async_manager.connection() as conn:
                cursor = await conn.execute("SELECT name FROM test_items")
                async_items = [row[0] async for row in cursor]
                assert async_items == ["async_item"]

            # Verify sync manager only sees sync data
            with sync_manager.connection() as conn:
                cursor = conn.execute("SELECT name FROM test_items")
                sync_items = [row[0] for row in cursor]
                assert sync_items == ["sync_item"]

        finally:
            await async_manager.close()
