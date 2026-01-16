"""Integration tests for ASGI middleware timing and response capture.

Tests that the middleware correctly:
- Captures HTTP status codes from http.response.start
- Measures request duration using perf_counter
- Accumulates response body size from http.response.body messages
- Passes through non-HTTP scopes unchanged
"""

import asyncio
import time
from typing import Any

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)

# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.Timing"),
]


# @tra: Adapter.ASGI.Middleware.Timing.StatusCode
async def test_middleware_captures_status_code():
    """Test that middleware captures status code from http.response.start."""
    captured_status = None

    async def app(scope: dict[str, Any], receive, send):
        """Simple app that sends a 201 status."""
        await send(
            {
                "type": "http.response.start",
                "status": 201,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"Created"})

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(app, log_storage, metrics_storage)

    # Create a wrapper to capture what status the middleware sees
    async def capturing_send(message):
        nonlocal captured_status
        if message["type"] == "http.response.start":
            captured_status = message["status"]

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/users",
        "query_string": b"",
        "headers": [],
    }

    async def mock_receive():
        """Mock receive that returns a future (not used in this test)."""
        return await asyncio.Future()

    await middleware(scope, mock_receive, capturing_send)
    assert captured_status == 201, "Middleware should pass through status code"


# @tra: Adapter.ASGI.Middleware.Timing.Duration
async def test_middleware_measures_request_duration():
    """Test that middleware measures request duration using perf_counter."""

    async def app(scope: dict[str, Any], receive, send):
        """App that takes measurable time."""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await asyncio.sleep(0.05)  # 50ms delay
        await send({"type": "http.response.body", "body": b"OK"})

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(app, log_storage, metrics_storage)

    start = time.perf_counter()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
    }

    async def mock_receive():
        """Mock receive (not used in this test)."""
        return await asyncio.Future()

    async def mock_send(_message):
        """No-op send for timing test."""
        await asyncio.sleep(0)

    await middleware(scope, mock_receive, mock_send)

    duration = time.perf_counter() - start
    assert duration >= 0.05, "Request should take at least 50ms"


# @tra: Adapter.ASGI.Middleware.Timing.StreamingResponse
async def test_middleware_handles_streaming_responses():
    """Test that middleware handles multiple http.response.body messages."""
    body_messages = []

    async def app(scope: dict[str, Any], receive, send):
        """App that streams response in chunks."""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        # Send response in 3 chunks
        await send({"type": "http.response.body", "body": b"chunk1", "more_body": True})
        await send({"type": "http.response.body", "body": b"chunk2", "more_body": True})
        await send(
            {"type": "http.response.body", "body": b"chunk3", "more_body": False}
        )

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(app, log_storage, metrics_storage)

    async def capturing_send(message):
        if message["type"] == "http.response.body":
            body_messages.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/stream",
        "query_string": b"",
        "headers": [],
    }

    async def mock_receive():
        """Mock receive (not used in this test)."""
        return await asyncio.Future()

    await middleware(scope, mock_receive, capturing_send)
    assert len(body_messages) == 3, "All body chunks should be sent"


# @tra: Adapter.ASGI.Middleware.Timing.ResponseBodySize
async def test_middleware_captures_response_body_size():
    """Test that middleware accumulates total response body size."""
    captured_bodies = []

    async def app(scope: dict[str, Any], receive, send):
        """App that sends multi-chunk response."""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"12345", "more_body": True})
        await send({"type": "http.response.body", "body": b"67890", "more_body": False})

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(app, log_storage, metrics_storage)

    async def capturing_send(message):
        if message["type"] == "http.response.body":
            captured_bodies.append(message["body"])

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/data",
        "query_string": b"",
        "headers": [],
    }

    async def mock_receive():
        """Mock receive (not used in this test)."""
        return await asyncio.Future()

    await middleware(scope, mock_receive, capturing_send)

    total_size = sum(len(body) for body in captured_bodies)
    assert total_size == 10, "Total body size should be 10 bytes"


# @tra: Adapter.ASGI.Middleware.Timing.NonHTTPPassthrough
async def test_middleware_passes_through_non_http_requests():
    """Test that middleware passes through non-HTTP scopes unchanged."""
    lifespan_called = False

    async def app(scope: dict[str, Any], receive, send):
        """App that handles lifespan events."""
        nonlocal lifespan_called
        if scope["type"] == "lifespan":
            lifespan_called = True
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(app, log_storage, metrics_storage)

    startup_complete = False

    async def mock_receive():
        return {"type": "lifespan.startup"}

    async def mock_send(message):
        nonlocal startup_complete
        if message["type"] == "lifespan.startup.complete":
            startup_complete = True

    scope = {"type": "lifespan"}
    await middleware(scope, mock_receive, mock_send)

    assert lifespan_called, "Lifespan scope should be passed through to app"
    assert startup_complete, "Lifespan startup should complete"
