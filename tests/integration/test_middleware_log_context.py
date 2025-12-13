"""Integration tests for log_context with middleware patterns.

These tests verify that the log_context context manager works correctly
when used to inject request-scoped attributes (like request IDs) into all
logs within a request lifecycle.

Includes both simulation tests (fast, isolated) and real TestClient tests
that prove the async-aware ObservabilipyHandler works end-to-end.
"""

import asyncio
import logging

import pytest

from observabilipy import (
    ObservabilipyHandler,
    get_log_context,
    log_context,
)
from observabilipy.adapters.storage.in_memory import InMemoryLogStorage
from observabilipy.core.models import LogEntry


def _run_async(coro):
    """Run async code in a new event loop."""
    return asyncio.run(coro)


async def _collect_entries(storage: InMemoryLogStorage) -> list[LogEntry]:
    """Collect all entries from storage."""
    return [e async for e in storage.read()]


@pytest.mark.fastapi
class TestMiddlewareLogContextPattern:
    """Tests for log_context integration with middleware-like patterns.

    These tests verify the core log_context functionality that middleware
    depends on, using synchronous logger calls (which is how it works
    when used with a real ASGI server).
    """

    def test_log_context_injects_request_id_into_logs(self) -> None:
        """log_context adds request_id to all logs within the context."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("test_middleware_inject")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simulate middleware pattern
        with log_context(request_id="req-12345"):
            logger.info("Processing request")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1
        assert entries[0].attributes["request_id"] == "req-12345"

    def test_multiple_logs_share_same_request_context(self) -> None:
        """Multiple logs within same context all have the same attributes."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("test_middleware_multiple")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simulate middleware wrapping request lifecycle
        with log_context(request_id="shared-context-123"):
            logger.info("Request started")
            logger.info("Processing in handler")
            logger.info("Request completed")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 3

        # All entries should have the same request_id
        for entry in entries:
            assert entry.attributes["request_id"] == "shared-context-123"

    def test_request_id_isolated_between_sequential_requests(self) -> None:
        """Each request context is isolated from others."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("test_middleware_isolated")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simulate two sequential requests
        with log_context(request_id="first-request"):
            logger.info("Processing request")

        with log_context(request_id="second-request"):
            logger.info("Processing request")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 2

        # First entry should have first request ID
        assert entries[0].attributes["request_id"] == "first-request"
        # Second entry should have second request ID (not leaked from first)
        assert entries[1].attributes["request_id"] == "second-request"

    def test_nested_context_adds_attributes(self) -> None:
        """Nested log_context adds to parent context."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("test_middleware_nested")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simulate middleware setting request_id, handler adding user_id
        with log_context(request_id="nested-test"):
            with log_context(user_id=42):
                logger.info("Fetching user")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1

        # Should have both request_id (from outer) and user_id (from inner)
        assert entries[0].attributes["request_id"] == "nested-test"
        assert entries[0].attributes["user_id"] == 42

    def test_context_with_multiple_attributes(self) -> None:
        """Multiple context attributes can be set at once."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("test_middleware_multi_attr")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simulate middleware setting multiple attributes
        with log_context(
            request_id="multi-attr-test",
            method="GET",
            path="/api/data",
        ):
            logger.info("Getting data")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 1

        assert entries[0].attributes["request_id"] == "multi-attr-test"
        assert entries[0].attributes["method"] == "GET"
        assert entries[0].attributes["path"] == "/api/data"

    def test_context_restored_after_block(self) -> None:
        """Context is properly restored after the block exits."""
        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("test_middleware_restore")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log before context
        logger.info("Before request")

        with log_context(request_id="during-request"):
            logger.info("During request")

        # Log after context - should NOT have request_id
        logger.info("After request")

        entries = _run_async(_collect_entries(storage))
        assert len(entries) == 3

        # Before: no request_id
        assert "request_id" not in entries[0].attributes
        # During: has request_id
        assert entries[1].attributes["request_id"] == "during-request"
        # After: no request_id (restored)
        assert "request_id" not in entries[2].attributes


@pytest.mark.fastapi
class TestAsyncContextIsolation:
    """Tests for context isolation between concurrent async tasks.

    These tests verify that contextvars-based log_context properly isolates
    context between concurrent async tasks, which is essential for correct
    behavior in async web frameworks.
    """

    @pytest.mark.asyncio
    async def test_concurrent_tasks_have_isolated_context(self) -> None:
        """Concurrent async tasks each have their own isolated context."""
        results: list[tuple[str, str | None]] = []

        async def simulated_request(request_id: str) -> None:
            """Simulate a request handler with log_context."""
            with log_context(request_id=request_id):
                # Simulate some async work
                await asyncio.sleep(0.01)
                # Capture what context we see
                ctx = get_log_context()
                results.append((request_id, ctx.get("request_id")))

        # Run multiple "requests" concurrently
        await asyncio.gather(
            simulated_request("task-1"),
            simulated_request("task-2"),
            simulated_request("task-3"),
        )

        # Each task should have seen its own request_id
        assert len(results) == 3
        for expected_id, actual_id in results:
            assert actual_id == expected_id, f"Expected {expected_id}, got {actual_id}"

    @pytest.mark.asyncio
    async def test_nested_async_context_preserved(self) -> None:
        """Nested async operations preserve outer context."""
        captured_contexts: list[dict] = []

        async def inner_operation() -> None:
            """Inner async operation that should see parent context."""
            await asyncio.sleep(0.001)
            captured_contexts.append(get_log_context().copy())

        async def outer_handler(request_id: str) -> None:
            """Outer handler that sets context and calls inner."""
            with log_context(request_id=request_id):
                with log_context(handler="outer"):
                    await inner_operation()

        await outer_handler("outer-test")

        assert len(captured_contexts) == 1
        assert captured_contexts[0]["request_id"] == "outer-test"
        assert captured_contexts[0]["handler"] == "outer"


@pytest.mark.fastapi
class TestFastAPITestClientIntegration:
    """Tests proving ObservabilipyHandler works with FastAPI TestClient.

    These tests use the real FastAPI TestClient to validate that the
    async-aware emit() implementation works correctly end-to-end.
    """

    def test_handler_works_with_testclient(self) -> None:
        """ObservabilipyHandler can be used with FastAPI TestClient."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("testclient_handler")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        app = FastAPI()

        @app.get("/")
        async def root():
            logger.info("Handler processing request")
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200

        entries = _run_async(_collect_entries(storage))
        assert len(entries) >= 1
        assert any("Handler processing request" in e.message for e in entries)

    def test_log_context_attributes_in_testclient_requests(self) -> None:
        """log_context attributes appear in logs during TestClient requests."""
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from starlette.middleware.base import BaseHTTPMiddleware

        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("testclient_context")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        class TestMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                with log_context(request_id="test-123", path=str(request.url.path)):
                    logger.info("Request started")
                    response = await call_next(request)
                    logger.info("Request completed")
                    return response

        app = FastAPI()
        app.add_middleware(TestMiddleware)

        @app.get("/test")
        async def test_endpoint():
            logger.info("Inside handler")
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200

        entries = _run_async(_collect_entries(storage))

        # All log entries should have the context attributes
        assert len(entries) >= 3
        for entry in entries:
            assert entry.attributes.get("request_id") == "test-123"
            assert entry.attributes.get("path") == "/test"

    def test_multiple_requests_have_isolated_context(self) -> None:
        """Multiple sequential requests via TestClient have isolated context."""
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from starlette.middleware.base import BaseHTTPMiddleware

        storage = InMemoryLogStorage()
        handler = ObservabilipyHandler(storage, context_provider=get_log_context)

        logger = logging.getLogger("testclient_isolation")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        request_counter = [0]

        class CountingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                request_counter[0] += 1
                req_id = f"req-{request_counter[0]}"
                with log_context(request_id=req_id):
                    logger.info(f"Processing {req_id}")
                    response = await call_next(request)
                    return response

        app = FastAPI()
        app.add_middleware(CountingMiddleware)

        @app.get("/")
        async def root():
            return {"ok": True}

        client = TestClient(app)
        client.get("/")
        client.get("/")
        client.get("/")

        entries = _run_async(_collect_entries(storage))

        assert len(entries) == 3
        assert entries[0].attributes["request_id"] == "req-1"
        assert entries[1].attributes["request_id"] == "req-2"
        assert entries[2].attributes["request_id"] == "req-3"
