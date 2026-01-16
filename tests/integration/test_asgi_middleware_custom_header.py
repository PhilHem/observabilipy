"""Tests for ASGI middleware custom request ID header configuration."""

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware
from observabilipy.adapters.storage.in_memory import InMemoryLogStorage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.CustomHeader"),
]


async def basic_asgi_app(scope, receive, send):
    """Basic ASGI app that returns 200 OK."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"OK"})


@pytest.mark.asyncio
async def test_middleware_uses_custom_request_id_header():
    """Middleware should accept request_id_header parameter in constructor.

    This test verifies that the middleware can be instantiated with a custom
    request_id_header parameter that will be used for extracting request IDs.
    """
    log_storage = InMemoryLogStorage()

    # Should accept request_id_header parameter
    middleware = ASGIObservabilityMiddleware(
        app=basic_asgi_app,
        log_storage=log_storage,
        metrics_storage=None,
        request_id_header="X-Correlation-ID",
    )

    assert middleware.request_id_header == "X-Correlation-ID"


@pytest.mark.asyncio
async def test_middleware_extracts_from_custom_header():
    """Middleware should extract request ID from custom header name.

    When configured with request_id_header="X-Correlation-ID", the middleware
    should look for that header instead of X-Request-ID.
    """
    log_storage = InMemoryLogStorage()
    middleware = ASGIObservabilityMiddleware(
        app=basic_asgi_app,
        log_storage=log_storage,
        metrics_storage=None,
        request_id_header="X-Correlation-ID",
    )

    # Simulate ASGI scope with custom header
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [
            [b"x-correlation-id", b"corr-999"],
        ],
    }

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        pass

    await middleware(scope, receive, send)

    # Verify log entry has correct request_id from custom header
    logs = [log async for log in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].attributes["request_id"] == "corr-999"


@pytest.mark.asyncio
async def test_middleware_falls_back_to_generated_id():
    """Middleware should generate UUID if custom header is not present.

    When configured with a custom header but the request doesn't include it,
    the middleware should fall back to generating a UUID.
    """
    log_storage = InMemoryLogStorage()
    middleware = ASGIObservabilityMiddleware(
        app=basic_asgi_app,
        log_storage=log_storage,
        metrics_storage=None,
        request_id_header="X-Correlation-ID",
    )

    # Simulate ASGI scope without the custom header
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        pass

    await middleware(scope, receive, send)

    # Verify log entry has a generated UUID request_id
    logs = [log async for log in log_storage.read()]
    assert len(logs) == 1
    request_id = logs[0].attributes["request_id"]
    # UUID format check: should have dashes
    assert "-" in request_id
    assert len(request_id) == 36  # UUID4 format length
