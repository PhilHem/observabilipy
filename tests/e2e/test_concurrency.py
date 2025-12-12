"""E2E tests for concurrent access to SQLite storage.

Tests that WAL mode enables concurrent reads and writes without errors.
"""

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.sqlite import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.core.models import LogEntry, MetricSample


@pytest.mark.e2e
class TestConcurrentWrites:
    """Test concurrent write operations to SQLite storage."""

    async def test_concurrent_log_writes_all_succeed(
        self,
        sqlite_log_db_path: str,
    ) -> None:
        """Multiple concurrent log writes all complete without errors."""
        storage = SQLiteLogStorage(sqlite_log_db_path)
        num_writes = 100

        async def write_log(i: int) -> None:
            await storage.write(
                LogEntry(
                    timestamp=float(i + 1),  # Start from 1, not 0 (read uses > 0)
                    level="INFO",
                    message=f"Concurrent log {i}",
                    attributes={"index": i},
                )
            )

        # Fire all writes concurrently
        await asyncio.gather(*[write_log(i) for i in range(num_writes)])

        # Verify all writes succeeded
        entries = [e async for e in storage.read()]
        assert len(entries) == num_writes

    async def test_concurrent_metric_writes_all_succeed(
        self,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Multiple concurrent metric writes all complete without errors."""
        storage = SQLiteMetricsStorage(sqlite_metrics_db_path)
        num_writes = 100

        async def write_metric(i: int) -> None:
            await storage.write(
                MetricSample(
                    name="concurrent_counter",
                    timestamp=float(i + 1),  # Start from 1, not 0
                    value=float(i),
                    labels={"index": str(i)},
                )
            )

        # Fire all writes concurrently
        await asyncio.gather(*[write_metric(i) for i in range(num_writes)])

        # Verify all writes succeeded
        # Note: read(since=0) returns samples with timestamp > 0
        samples = [s async for s in storage.read()]
        assert len(samples) == num_writes


@pytest.mark.e2e
class TestConcurrentReadsAndWrites:
    """Test concurrent read and write operations."""

    async def test_reads_during_writes_succeed(
        self,
        sqlite_log_db_path: str,
    ) -> None:
        """Reads can proceed while writes are happening (WAL mode)."""
        storage = SQLiteLogStorage(sqlite_log_db_path)

        # Pre-populate some data (start from 1, not 0)
        for i in range(10):
            await storage.write(
                LogEntry(
                    timestamp=float(i + 1),
                    level="INFO",
                    message=f"Initial {i}",
                    attributes={},
                )
            )

        read_results: list[int] = []
        write_count = 50

        async def do_reads() -> None:
            """Continuously read while writes are happening."""
            for _ in range(20):
                entries = [e async for e in storage.read()]
                read_results.append(len(entries))
                await asyncio.sleep(0.001)

        async def do_writes() -> None:
            """Write new entries."""
            for i in range(write_count):
                await storage.write(
                    LogEntry(
                        timestamp=float(100 + i),
                        level="INFO",
                        message=f"During reads {i}",
                        attributes={},
                    )
                )

        # Run reads and writes concurrently
        await asyncio.gather(do_reads(), do_writes())

        # All reads should have succeeded (got some count)
        assert len(read_results) == 20
        assert all(count >= 10 for count in read_results)  # At least initial data

        # All writes should have succeeded
        final_entries = [e async for e in storage.read()]
        assert len(final_entries) == 10 + write_count


@pytest.mark.e2e
class TestConcurrentHTTPRequests:
    """Test concurrent HTTP requests to endpoints."""

    async def test_concurrent_scrape_requests(
        self,
        sqlite_log_db_path: str,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Multiple concurrent /logs requests all succeed."""
        log_storage = SQLiteLogStorage(sqlite_log_db_path)
        metrics_storage = SQLiteMetricsStorage(sqlite_metrics_db_path)

        # Pre-populate data (start from 1, not 0)
        for i in range(20):
            await log_storage.write(
                LogEntry(
                    timestamp=float(i + 1),
                    level="INFO",
                    message=f"Log {i}",
                    attributes={},
                )
            )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Fire 20 concurrent requests
            responses = await asyncio.gather(*[client.get("/logs") for _ in range(20)])

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
        # All should return the same data (Log 1 is our first entry)
        assert all("Log 1" in r.text for r in responses)

    async def test_concurrent_writes_and_scrapes_via_http(
        self,
        sqlite_log_db_path: str,
        sqlite_metrics_db_path: str,
    ) -> None:
        """Concurrent writes to storage while scraping via HTTP."""
        log_storage = SQLiteLogStorage(sqlite_log_db_path)
        metrics_storage = SQLiteMetricsStorage(sqlite_metrics_db_path)

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))

        scrape_results: list[int] = []
        num_writes = 50

        async def do_writes() -> None:
            """Write logs directly to storage."""
            for i in range(num_writes):
                await log_storage.write(
                    LogEntry(
                        timestamp=float(i + 1),  # Start from 1, not 0
                        level="INFO",
                        message=f"Concurrent {i}",
                        attributes={},
                    )
                )
                await asyncio.sleep(0.001)

        async def do_scrapes(client: httpx.AsyncClient) -> None:
            """Scrape via HTTP while writes happen."""
            for _ in range(20):
                response = await client.get("/logs")
                assert response.status_code == 200
                lines = [line for line in response.text.strip().split("\n") if line]
                scrape_results.append(len(lines))
                await asyncio.sleep(0.002)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await asyncio.gather(do_writes(), do_scrapes(client))

        # All scrapes succeeded
        assert len(scrape_results) == 20
        # Scrapes should show increasing counts as writes progress
        # (not strictly monotonic due to timing, but final should have all)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as final_client:
            final_response = await final_client.get("/logs")
        final_lines = [line for line in final_response.text.strip().split("\n") if line]
        assert len(final_lines) == num_writes


@pytest.mark.e2e
class TestWALModeEnabled:
    """Verify WAL mode is actually enabled."""

    async def test_wal_mode_is_active(
        self,
        sqlite_log_db_path: str,
    ) -> None:
        """Confirm SQLite is running in WAL journal mode."""
        import aiosqlite

        storage = SQLiteLogStorage(sqlite_log_db_path)
        # Trigger connection to create database
        await storage.write(
            LogEntry(timestamp=1.0, level="INFO", message="test", attributes={})
        )

        # Check journal mode directly
        async with aiosqlite.connect(sqlite_log_db_path) as db:
            async with db.execute("PRAGMA journal_mode") as cursor:
                row = await cursor.fetchone()
                assert row is not None
                assert row[0].lower() == "wal"
