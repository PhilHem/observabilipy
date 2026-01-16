"""Test ASGI middleware HTTP request counter metrics."""

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware
from observabilipy.adapters.storage.in_memory import InMemoryMetricsStorage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.Metrics"),
]


@pytest.mark.asyncio
async def test_middleware_increments_request_counter(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that middleware increments the request counter for each HTTP request."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    # Send first request
    await middleware(asgi_scope(method="GET", path="/api/users"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    counters = [m for m in metrics if m.name == "http_requests_total"]
    assert len(counters) == 1, "Should have 1 counter after first request"

    # Send second request
    await middleware(asgi_scope(method="POST", path="/api/users"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    counters = [m for m in metrics if m.name == "http_requests_total"]
    assert len(counters) == 2, "Should have 2 counters after second request"


@pytest.mark.asyncio
async def test_middleware_counter_has_method_label(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the counter metric includes the HTTP method label."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="POST", path="/test"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    counters = [m for m in metrics if m.name == "http_requests_total"]
    assert len(counters) == 1
    assert counters[0].labels["method"] == "POST"


@pytest.mark.asyncio
async def test_middleware_counter_has_path_label(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the counter metric includes the request path label."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="GET", path="/api/v1/users"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    counters = [m for m in metrics if m.name == "http_requests_total"]
    assert len(counters) == 1
    assert counters[0].labels["path"] == "/api/v1/users"


@pytest.mark.asyncio
async def test_middleware_counter_has_status_label(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the counter metric includes the response status label."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="GET", path="/test"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    counters = [m for m in metrics if m.name == "http_requests_total"]
    assert len(counters) == 1
    assert counters[0].labels["status"] == "200"


@pytest.mark.asyncio
async def test_middleware_counter_name_is_http_requests_total(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the counter metric uses the name 'http_requests_total'."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="GET", path="/test"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    counters = [m for m in metrics if m.name == "http_requests_total"]
    assert len(counters) == 1
