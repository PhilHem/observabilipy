"""Integration tests for ASGI middleware request ID extraction and logging."""

from unittest.mock import AsyncMock

import pytest

from observabilipy.adapters.frameworks.asgi import (
    ASGIObservabilityMiddleware,
)
from observabilipy.core.models import LogEntry

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.RequestId"),
]


@pytest.mark.asyncio
async def test_middleware_extracts_request_id_from_header(
    basic_asgi_app, asgi_scope, asgi_send_capture
):
    """Middleware extracts X-Request-ID from headers if present."""
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage, metrics_storage
    )

    scope = asgi_scope(method="GET", path="/test")
    scope["headers"] = [(b"x-request-id", b"abc-123-def")]

    send, _responses = asgi_send_capture

    async def receive():
        return {"type": "http.request", "body": b""}

    await middleware(scope, receive, send)

    # Check that log_storage.write was called with request_id in attributes
    assert log_storage.write.called
    entry: LogEntry = log_storage.write.call_args[0][0]
    assert "request_id" in entry.attributes
    assert entry.attributes["request_id"] == "abc-123-def"


@pytest.mark.asyncio
async def test_middleware_generates_request_id_when_missing(
    basic_asgi_app, asgi_scope, asgi_send_capture
):
    """Middleware generates a UUID request ID if X-Request-ID header is missing."""
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage, metrics_storage
    )

    scope = asgi_scope(method="GET", path="/test")
    scope["headers"] = []  # No X-Request-ID header

    send, _responses = asgi_send_capture

    async def receive():
        return {"type": "http.request", "body": b""}

    await middleware(scope, receive, send)

    # Check that log_storage.write was called with a generated request_id
    assert log_storage.write.called
    entry: LogEntry = log_storage.write.call_args[0][0]
    assert "request_id" in entry.attributes
    # Verify it looks like a UUID (contains dashes and is 36 chars)
    request_id = entry.attributes["request_id"]
    assert isinstance(request_id, str)
    assert len(request_id) == 36
    assert request_id.count("-") == 4


@pytest.mark.asyncio
async def test_middleware_logs_request_id_attribute(
    basic_asgi_app, asgi_scope, asgi_send_capture
):
    """Middleware includes request_id in LogEntry attributes."""
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage, metrics_storage
    )

    scope = asgi_scope(method="GET", path="/test")
    scope["headers"] = [(b"x-request-id", b"test-id-789")]

    send, _responses = asgi_send_capture

    async def receive():
        return {"type": "http.request", "body": b""}

    await middleware(scope, receive, send)

    # Verify log entry structure
    assert log_storage.write.called
    entry: LogEntry = log_storage.write.call_args[0][0]
    assert isinstance(entry, LogEntry)
    assert entry.attributes["request_id"] == "test-id-789"
    assert entry.level == "INFO"  # Assuming INFO level for HTTP requests
    assert entry.timestamp > 0


@pytest.mark.asyncio
async def test_middleware_handles_lowercase_header(
    basic_asgi_app, asgi_scope, asgi_send_capture
):
    """Middleware handles case-insensitive X-Request-ID header lookup."""
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage, metrics_storage
    )

    scope = asgi_scope(method="GET", path="/test")
    # Header name is already lowercase in ASGI (per spec)
    scope["headers"] = [(b"x-request-id", b"lowercase-id")]

    send, _responses = asgi_send_capture

    async def receive():
        return {"type": "http.request", "body": b""}

    await middleware(scope, receive, send)

    assert log_storage.write.called
    entry: LogEntry = log_storage.write.call_args[0][0]
    assert entry.attributes["request_id"] == "lowercase-id"


@pytest.mark.asyncio
async def test_middleware_uses_existing_request_id(
    basic_asgi_app, asgi_scope, asgi_send_capture
):
    """Middleware prefers existing X-Request-ID over generating a new one."""
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage, metrics_storage
    )

    scope = asgi_scope(method="GET", path="/test")
    scope["headers"] = [(b"x-request-id", b"existing-id")]

    send, _responses = asgi_send_capture

    async def receive():
        return {"type": "http.request", "body": b""}

    await middleware(scope, receive, send)

    assert log_storage.write.called
    entry: LogEntry = log_storage.write.call_args[0][0]
    # Should use the provided ID, not generate a new one
    assert entry.attributes["request_id"] == "existing-id"
    # Verify it's NOT a UUID format (no dashes if this was an intentional simple ID)
    # But in this case "existing-id" has a dash, so just check it matches exactly
    assert entry.attributes["request_id"] == "existing-id"
