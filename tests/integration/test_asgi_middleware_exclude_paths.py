"""Tests for ASGI middleware exclude_paths feature.

Tests that ASGIObservabilityMiddleware can skip logging and metrics for
specified paths using exact matching and wildcard patterns.
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
    pytest.mark.tra("Adapter.ASGI.Middleware.ExcludePaths"),
]


async def _basic_app(scope, receive, send):
    """Basic ASGI app that returns 200 OK."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"OK"})


async def _make_scope(path: str) -> dict:
    """Create ASGI scope for testing."""
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
    }


async def _receive():
    """Async receive stub."""
    return {"type": "http.request", "body": b""}


async def _send(message):
    """Async send stub."""
    pass


# @tra: Adapter.ASGI.Middleware.ExcludePaths.DefaultEmpty
@pytest.mark.asyncio
async def test_middleware_exclude_paths_default_empty():
    """Test that exclude_paths defaults to empty list when not provided."""
    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()

    middleware = ASGIObservabilityMiddleware(
        app=_basic_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
    )

    assert middleware.exclude_paths == []


# @tra: Adapter.ASGI.Middleware.ExcludePaths.ExactMatch
@pytest.mark.asyncio
async def test_middleware_skips_excluded_paths():
    """Test that middleware skips logging/metrics for exact path matches."""
    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()

    middleware = ASGIObservabilityMiddleware(
        app=_basic_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
        exclude_paths=["/health", "/readiness"],
    )

    scope = await _make_scope("/health")
    await middleware(scope, _receive, _send)

    # No logs or metrics should be written for excluded path
    logs = [log async for log in log_storage.read()]
    metrics = [m async for m in metrics_storage.read()]

    assert len(logs) == 0, "Expected no logs for excluded /health path"
    assert len(metrics) == 0, "Expected no metrics for excluded /health path"


# @tra: Adapter.ASGI.Middleware.ExcludePaths.WildcardMatch
@pytest.mark.asyncio
async def test_middleware_skips_wildcard_paths():
    """Test that middleware skips paths matching wildcard patterns."""
    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()

    middleware = ASGIObservabilityMiddleware(
        app=_basic_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
        exclude_paths=["/internal/*", "/admin/*"],
    )

    # Test /internal/* wildcard
    scope = await _make_scope("/internal/debug")
    await middleware(scope, _receive, _send)

    logs = [log async for log in log_storage.read()]
    metrics = [m async for m in metrics_storage.read()]

    assert len(logs) == 0, "Expected no logs for excluded /internal/* path"
    assert len(metrics) == 0, "Expected no metrics for excluded /internal/* path"

    # Test /admin/* wildcard
    scope = await _make_scope("/admin/metrics")
    await middleware(scope, _receive, _send)

    logs = [log async for log in log_storage.read()]
    metrics = [m async for m in metrics_storage.read()]

    assert len(logs) == 0, "Expected no logs for excluded /admin/* path"
    assert len(metrics) == 0, "Expected no metrics for excluded /admin/* path"


# @tra: Adapter.ASGI.Middleware.ExcludePaths.NonMatch
@pytest.mark.asyncio
async def test_middleware_logs_non_excluded_paths():
    """Test that middleware logs/metrics for paths NOT in exclude list."""
    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()

    middleware = ASGIObservabilityMiddleware(
        app=_basic_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
        exclude_paths=["/health"],
    )

    scope = await _make_scope("/api/users")
    await middleware(scope, _receive, _send)

    # Logs and metrics SHOULD be written for non-excluded path
    logs = [log async for log in log_storage.read()]
    metrics = [m async for m in metrics_storage.read()]

    assert len(logs) == 1, "Expected 1 log entry for non-excluded path"
    assert logs[0].attributes["path"] == "/api/users"

    # Metrics should include counter + histogram
    assert len(metrics) == 2, "Expected counter + histogram metrics"
    counter = [m for m in metrics if m.name == "http_requests_total"]
    histogram = [m for m in metrics if m.name == "http_request_duration_seconds"]
    assert len(counter) == 1, "Expected 1 counter metric"
    assert len(histogram) == 1, "Expected 1 histogram metric"
