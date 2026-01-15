"""Tests for ASGI middleware auto-instrumentation.

This module tests the ASGIObservabilityMiddleware class that wraps ASGI applications
to automatically capture request/response metrics and logs.
"""

import pytest

from observabilipy.adapters.frameworks.asgi import (
    ASGIObservabilityMiddleware,
    Receive,
    Scope,
    Send,
)
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.Middleware.Init")
def test_middleware_init_accepts_app_and_storage():
    """ASGIObservabilityMiddleware should accept app and storage adapters."""

    # Arrange: Create a minimal ASGI app
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()

    # Act: Initialize middleware
    middleware = ASGIObservabilityMiddleware(
        app=app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    # Assert: Middleware should store references
    assert middleware.app is app
    assert middleware.log_storage is log_storage
    assert middleware.metrics_storage is metrics_storage


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.Middleware.Interface")
@pytest.mark.asyncio
async def test_middleware_is_callable_asgi_interface():
    """ASGIObservabilityMiddleware should implement ASGI __call__ interface."""

    # Arrange: Create a minimal ASGI app
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    middleware = ASGIObservabilityMiddleware(
        app=app,
        log_storage=InMemoryLogStorage(),
        metrics_storage=InMemoryMetricsStorage(),
    )

    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b""}

    responses: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        responses.append(message)

    # Act: Call middleware as ASGI app
    await middleware(scope, receive, send)

    # Assert: Middleware should be callable and process request
    # For now, just verify it doesn't raise an exception
    assert True  # Basic check that __call__ completed


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.Middleware.Passthrough")
@pytest.mark.asyncio
async def test_middleware_passes_through_to_wrapped_app():
    """ASGIObservabilityMiddleware should pass requests through to wrapped app."""

    # Arrange: Create an ASGI app that returns specific response
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 201,
                "headers": [(b"x-custom", b"test")],
            }
        )
        await send({"type": "http.response.body", "body": b"Custom Response"})

    middleware = ASGIObservabilityMiddleware(
        app=app,
        log_storage=InMemoryLogStorage(),
        metrics_storage=InMemoryMetricsStorage(),
    )

    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/custom",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b""}

    responses: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        responses.append(message)

    # Act: Call middleware
    await middleware(scope, receive, send)

    # Assert: Response should match wrapped app's response
    assert len(responses) == 2
    assert responses[0]["type"] == "http.response.start"
    assert responses[0]["status"] == 201
    assert (b"x-custom", b"test") in responses[0]["headers"]
    assert responses[1]["type"] == "http.response.body"
    assert responses[1]["body"] == b"Custom Response"
