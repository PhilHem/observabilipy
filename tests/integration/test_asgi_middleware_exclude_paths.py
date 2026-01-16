"""Tests for ASGI middleware exclude_paths feature.

Tests that ASGIObservabilityMiddleware can skip logging and metrics for
specified paths using exact matching and wildcard patterns.
"""

from unittest.mock import AsyncMock

import pytest

from observabilipy.adapters.frameworks.asgi import ASGIObservabilityMiddleware

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tier(2),
    pytest.mark.tra("Adapter.ASGI.Middleware.ExcludePaths"),
]


# @tra: Adapter.ASGI.Middleware.ExcludePaths.DefaultEmpty
async def test_middleware_exclude_paths_default_empty():
    """Test that exclude_paths defaults to empty list when not provided."""
    app = AsyncMock()
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        app=app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
    )

    assert middleware.exclude_paths == []


# @tra: Adapter.ASGI.Middleware.ExcludePaths.ExactMatch
async def test_middleware_skips_excluded_paths():
    """Test that middleware skips logging/metrics for exact path matches."""
    app = AsyncMock()
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        app=app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
        exclude_paths=["/health", "/readiness"],
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
    }
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    # App should still be called
    app.assert_called_once()

    # But no logs or metrics should be written
    log_storage.write.assert_not_called()
    metrics_storage.write.assert_not_called()


# @tra: Adapter.ASGI.Middleware.ExcludePaths.WildcardMatch
async def test_middleware_skips_wildcard_paths():
    """Test that middleware skips paths matching wildcard patterns."""
    app = AsyncMock()
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    middleware = ASGIObservabilityMiddleware(
        app=app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
        exclude_paths=["/internal/*", "/admin/*"],
    )

    # Test /internal/* wildcard
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/internal/debug",
        "headers": [],
    }
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    app.assert_called_once()
    log_storage.write.assert_not_called()
    metrics_storage.write.assert_not_called()

    # Reset mocks and test /admin/* wildcard
    app.reset_mock()
    scope["path"] = "/admin/metrics"
    await middleware(scope, receive, send)

    app.assert_called_once()
    log_storage.write.assert_not_called()
    metrics_storage.write.assert_not_called()


# @tra: Adapter.ASGI.Middleware.ExcludePaths.NonMatch
async def test_middleware_logs_non_excluded_paths():
    """Test that middleware logs/metrics for paths NOT in exclude list."""
    log_storage = AsyncMock()
    metrics_storage = AsyncMock()

    # Mock app that sends proper ASGI response
    async def mock_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"OK"})

    middleware = ASGIObservabilityMiddleware(
        app=mock_app,
        log_storage=log_storage,
        metrics_storage=metrics_storage,
        exclude_paths=["/health"],
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/users",
        "headers": [],
    }
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    # Logs and metrics SHOULD be written for non-excluded path
    log_storage.write.assert_called_once()
    # Metrics should be written twice: counter + histogram
    assert metrics_storage.write.call_count == 2
