"""BDD step definitions for middleware observability features."""

from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_bdd import given

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

# === Request/Response Capture ===


@dataclass
class RequestCapture:
    """Utility for recording request/response pairs in tests.

    Used by step definitions to capture HTTP exchanges during
    middleware testing for later assertions.
    """

    method: str = ""
    path: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int = 0
    response_body: str = ""
    exception: Exception | None = None


# === Scenario Context ===


@dataclass
class MiddlewareScenarioContext:
    """Shared state between steps in a middleware scenario."""

    log_storage: InMemoryLogStorage = field(default_factory=InMemoryLogStorage)
    metrics_storage: InMemoryMetricsStorage = field(
        default_factory=InMemoryMetricsStorage
    )
    app: Any = None
    request_capture: RequestCapture = field(default_factory=RequestCapture)


@pytest.fixture
def ctx() -> MiddlewareScenarioContext:
    """Fresh scenario context for each test."""
    return MiddlewareScenarioContext()


# === Background Steps ===


@given("in-memory log storage")
def given_inmemory_log_storage(ctx: MiddlewareScenarioContext) -> None:
    """Initialize in-memory log storage."""
    ctx.log_storage = InMemoryLogStorage()


@given("in-memory metrics storage")
def given_inmemory_metrics_storage(ctx: MiddlewareScenarioContext) -> None:
    """Initialize in-memory metrics storage."""
    ctx.metrics_storage = InMemoryMetricsStorage()


@given("an ASGI app with observability middleware")
def given_asgi_app_with_middleware(ctx: MiddlewareScenarioContext) -> None:
    """Create test ASGI app with observability middleware."""

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        """Simple test ASGI app that returns 200 OK."""
        if scope["type"] == "http":
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )
