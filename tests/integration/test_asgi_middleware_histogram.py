"""Test ASGI middleware HTTP request duration histogram metrics."""

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware
from observabilipy.adapters.storage.in_memory import InMemoryMetricsStorage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.Histogram"),
]


@pytest.mark.asyncio
async def test_middleware_records_duration_histogram(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that middleware records a histogram metric for request duration."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    # Send request
    await middleware(asgi_scope(method="GET", path="/api/users"), lambda: None, send)

    # Should have both counter and histogram
    metrics = [m async for m in metrics_storage.read()]
    histogram_metrics = [
        m for m in metrics if m.name == "http_request_duration_seconds"
    ]
    assert len(histogram_metrics) == 1, "Should have 1 histogram metric"


@pytest.mark.asyncio
async def test_histogram_has_method_label(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the histogram metric includes the HTTP method label."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="POST", path="/test"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    histogram_metrics = [
        m for m in metrics if m.name == "http_request_duration_seconds"
    ]
    assert len(histogram_metrics) == 1
    assert histogram_metrics[0].labels["method"] == "POST"


@pytest.mark.asyncio
async def test_histogram_has_path_label(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the histogram metric includes the request path label."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="GET", path="/api/v1/users"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    histogram_metrics = [
        m for m in metrics if m.name == "http_request_duration_seconds"
    ]
    assert len(histogram_metrics) == 1
    assert histogram_metrics[0].labels["path"] == "/api/v1/users"


@pytest.mark.asyncio
async def test_histogram_name_is_http_request_duration_seconds(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the histogram metric uses the name 'http_request_duration_seconds'."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="GET", path="/test"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    histogram_metrics = [
        m for m in metrics if m.name == "http_request_duration_seconds"
    ]
    assert len(histogram_metrics) == 1
    assert histogram_metrics[0].name == "http_request_duration_seconds"


@pytest.mark.asyncio
async def test_histogram_value_matches_duration(
    basic_asgi_app, asgi_scope, asgi_send_capture, log_storage
):
    """Test that the histogram value is the duration in seconds."""
    metrics_storage = InMemoryMetricsStorage()
    middleware = ASGIObservabilityMiddleware(
        basic_asgi_app, log_storage=log_storage, metrics_storage=metrics_storage
    )

    send, _responses = asgi_send_capture

    await middleware(asgi_scope(method="GET", path="/test"), lambda: None, send)
    metrics = [m async for m in metrics_storage.read()]
    histogram_metrics = [
        m for m in metrics if m.name == "http_request_duration_seconds"
    ]
    assert len(histogram_metrics) == 1
    # Duration should be small but positive (measured in seconds, not ms)
    assert histogram_metrics[0].value > 0
    assert histogram_metrics[0].value < 1.0  # Should complete in less than 1 second
