"""Integration tests for ASGI middleware log levels.

Tests verify that ASGIObservabilityMiddleware determines log level based on
HTTP status code:
- 200-299 (2xx) → INFO
- 400-499 (4xx) → WARN
- 500-599 (5xx) → ERROR
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
    pytest.mark.tra("Adapter.ASGI.Middleware.LogLevels"),
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
async def test_middleware_logs_info_for_2xx_status(log_storage, metrics_storage):
    """Test that middleware logs INFO level for 2xx status codes."""

    async def app_200(scope, receive, send):
        """App that returns 200 OK."""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"OK"})

    middleware = ASGIObservabilityMiddleware(app_200, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].level == "INFO"


@pytest.mark.asyncio
async def test_middleware_logs_warn_for_4xx_status(log_storage, metrics_storage):
    """Test that middleware logs WARN level for 4xx status codes."""

    async def app_400(scope, receive, send):
        """App that returns 400 Bad Request."""
        await send(
            {
                "type": "http.response.start",
                "status": 400,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"Bad Request"})

    middleware = ASGIObservabilityMiddleware(app_400, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/users",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].level == "WARN"


@pytest.mark.asyncio
async def test_middleware_logs_error_for_5xx_status(log_storage, metrics_storage):
    """Test that middleware logs ERROR level for 5xx status codes."""

    async def app_500(scope, receive, send):
        """App that returns 500 Internal Server Error."""
        await send(
            {
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"Internal Server Error"})

    middleware = ASGIObservabilityMiddleware(app_500, log_storage, metrics_storage)
    send_capture = SendCapture()

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/error",
    }

    await middleware(scope, noop_receive, send_capture)

    logs = [entry async for entry in log_storage.read()]
    assert len(logs) == 1
    assert logs[0].level == "ERROR"
