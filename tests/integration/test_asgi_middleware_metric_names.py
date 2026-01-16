"""Tests for ASGIObservabilityMiddleware custom metric names."""

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.MetricNames"),
]


@pytest.fixture
async def async_log_storage() -> InMemoryLogStorage:
    """Provide async in-memory log storage."""
    return InMemoryLogStorage()


@pytest.fixture
async def async_metrics_storage() -> InMemoryMetricsStorage:
    """Provide async in-memory metrics storage."""
    return InMemoryMetricsStorage()


async def _create_basic_app(
    log_storage: LogStoragePort | None,
    metrics_storage: MetricsStoragePort | None,
) -> ASGIObservabilityMiddleware:
    """Create a simple ASGI app that returns 200 OK."""

    async def simple_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"OK",
            }
        )

    return ASGIObservabilityMiddleware(
        simple_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
    )


@pytest.mark.asyncio
async def test_middleware_uses_custom_counter_name(
    async_log_storage: InMemoryLogStorage,
    async_metrics_storage: InMemoryMetricsStorage,
) -> None:
    """Test that middleware uses custom counter metric name."""
    middleware = await _create_basic_app(
        log_storage=async_log_storage,
        metrics_storage=async_metrics_storage,
    )

    # Set custom counter name
    custom_name = "custom_http_requests"
    middleware.set_request_counter_name(custom_name)

    # Create a mock ASGI scope for GET /test
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.disconnect"}

    messages: list[dict] = []

    async def send(message: dict) -> None:
        messages.append(message)

    # Call middleware
    await middleware(scope, receive, send)

    # Assert custom counter metric was written
    metrics = [metric async for metric in async_metrics_storage.read()]
    assert len(metrics) >= 1, "Expected metrics to be recorded"

    # Find counter metric by name
    counter_metrics = [m for m in metrics if m.name == custom_name]
    assert len(counter_metrics) >= 1, (
        f"Expected metric named '{custom_name}', but got {[m.name for m in metrics]}"
    )

    # Default counter name should NOT be used
    default_metrics = [m for m in metrics if m.name == "http_requests_total"]
    assert len(default_metrics) == 0, (
        f"Expected no default name, found {len(default_metrics)} metrics"
    )


@pytest.mark.asyncio
async def test_middleware_uses_custom_histogram_name(
    async_log_storage: InMemoryLogStorage,
    async_metrics_storage: InMemoryMetricsStorage,
) -> None:
    """Test that middleware uses custom histogram metric name."""
    middleware = await _create_basic_app(
        log_storage=async_log_storage,
        metrics_storage=async_metrics_storage,
    )

    # Set custom histogram name
    custom_name = "custom_http_duration"
    middleware.set_request_histogram_name(custom_name)

    # Create a mock ASGI scope for GET /test
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.disconnect"}

    messages: list[dict] = []

    async def send(message: dict) -> None:
        messages.append(message)

    # Call middleware
    await middleware(scope, receive, send)

    # Assert custom histogram metric was written
    metrics = [metric async for metric in async_metrics_storage.read()]
    assert len(metrics) >= 1, "Expected metrics to be recorded"

    # Find histogram metric by name
    histogram_metrics = [m for m in metrics if m.name == custom_name]
    assert len(histogram_metrics) >= 1, (
        f"Expected metric named '{custom_name}', but got {[m.name for m in metrics]}"
    )

    # Default histogram name should NOT be used
    default_metrics = [m for m in metrics if m.name == "http_request_duration_seconds"]
    assert len(default_metrics) == 0, (
        f"Expected no default name, found {len(default_metrics)} metrics"
    )
