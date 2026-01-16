"""Tests for ASGIObservabilityMiddleware record_metrics configuration."""

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
    pytest.mark.tra("Adapter.ASGI.Middleware.MetricsConfig"),
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
    record_metrics: bool = True,
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

    middleware = ASGIObservabilityMiddleware(
        simple_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
    )
    middleware.set_record_metrics(record_metrics)
    return middleware


@pytest.mark.asyncio
async def test_middleware_skips_metrics_when_disabled(
    async_log_storage: InMemoryLogStorage,
    async_metrics_storage: InMemoryMetricsStorage,
) -> None:
    """Test that middleware skips metrics when record_metrics=False."""
    middleware = await _create_basic_app(
        log_storage=async_log_storage,
        metrics_storage=async_metrics_storage,
        record_metrics=False,
    )

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

    # Assert no metrics were written
    metrics = [metric async for metric in async_metrics_storage.read()]
    assert len(metrics) == 0, "Expected no metrics when record_metrics=False"


@pytest.mark.asyncio
async def test_middleware_still_logs_when_metrics_disabled(
    async_log_storage: InMemoryLogStorage,
    async_metrics_storage: InMemoryMetricsStorage,
) -> None:
    """Test that middleware still logs when record_metrics=False."""
    middleware = await _create_basic_app(
        log_storage=async_log_storage,
        metrics_storage=async_metrics_storage,
        record_metrics=False,
    )

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

    # Assert metrics were NOT written
    metrics = [metric async for metric in async_metrics_storage.read()]
    assert len(metrics) == 0, "Expected no metrics when record_metrics=False"

    # Assert logs WERE written
    logs = [log async for log in async_log_storage.read()]
    assert len(logs) >= 1, "Expected logs to be recorded"
