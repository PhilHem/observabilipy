"""Integration tests for ASGI middleware logging functionality.

Tests verify that ASGIObservabilityMiddleware correctly captures and logs
HTTP request details including method, path, status code, and duration.
"""

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.Logging"),
]


# Fixtures for test setup
@pytest.fixture
def log_storage():
    """Create in-memory log storage for testing."""
    return InMemoryLogStorage()


@pytest.fixture
def metrics_storage():
    """Create in-memory metrics storage for testing."""
    return InMemoryMetricsStorage()


async def basic_app(scope, receive, send):
    """Basic ASGI app that returns 200 OK."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"OK"})


async def noop_receive():
    """Noop receive callable for testing."""
    return {"type": "http.request", "body": b""}


class SendCapture:
    """Captures messages sent through ASGI send callable."""

    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_middleware_logs_request_method(log_storage, metrics_storage):
    """Test that middleware captures HTTP method in log entry."""
    middleware = ASGIObservabilityMiddleware(basic_app, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/users",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].attributes.get("method") == "POST"


@pytest.mark.asyncio
async def test_middleware_logs_request_path(log_storage, metrics_storage):
    """Test that middleware captures request path in log entry."""
    middleware = ASGIObservabilityMiddleware(basic_app, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/products",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].attributes.get("path") == "/api/v1/products"


@pytest.mark.asyncio
async def test_middleware_logs_status_code(log_storage, metrics_storage):
    """Test that middleware captures HTTP status code in log entry."""

    async def app_404(scope, receive, send):
        """App that returns 404."""
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"Not Found"})

    middleware = ASGIObservabilityMiddleware(app_404, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/not-found",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].attributes.get("status_code") == 404


@pytest.mark.asyncio
async def test_middleware_logs_duration_ms(log_storage, metrics_storage):
    """Test that middleware captures request duration in milliseconds."""
    import asyncio

    async def slow_app(scope, receive, send):
        """App that takes at least 10ms to respond."""
        await asyncio.sleep(0.01)  # Sleep for 10ms
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"OK"})

    middleware = ASGIObservabilityMiddleware(slow_app, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/slow",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    duration_ms = logs[0].attributes.get("duration_ms")
    assert duration_ms is not None
    assert duration_ms >= 10.0  # At least 10ms due to sleep


@pytest.mark.asyncio
async def test_middleware_logs_complete_request_entry(log_storage, metrics_storage):
    """Test that middleware creates complete log entry with all HTTP attributes."""
    middleware = ASGIObservabilityMiddleware(basic_app, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "PUT",
        "path": "/api/items/123",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1

    entry = logs[0]
    # Verify log entry structure
    assert entry.level == "INFO"
    assert entry.message != ""  # Should have a meaningful message
    assert entry.timestamp > 0

    # Verify all HTTP attributes are present
    assert entry.attributes.get("method") == "PUT"
    assert entry.attributes.get("path") == "/api/items/123"
    assert entry.attributes.get("status_code") == 200
    assert entry.attributes.get("duration_ms") is not None
    assert entry.attributes.get("duration_ms") >= 0
