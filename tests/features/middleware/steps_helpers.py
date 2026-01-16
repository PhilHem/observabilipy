"""Shared helpers and fixtures for middleware BDD tests."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from observabilipy.adapters.frameworks.asgi import (
    ASGIObservabilityMiddleware,
    Receive,
    Scope,
    Send,
)
from observabilipy.adapters.logging_context import (
    clear_log_context,
    get_log_context,
)
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

# === Request/Response Capture ===


@dataclass
class RequestCapture:
    """Utility for recording request/response pairs in tests."""

    method: str = ""
    path: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int = 0
    response_body: str = ""
    exception: Exception | None = None


# === Scenario Context ===


@dataclass
class MiddlewareConfig:
    """Configuration options for middleware."""

    exclude_paths: list[str] = field(default_factory=list)
    request_id_header: str = "X-Request-ID"
    log_requests: bool = True
    record_metrics: bool = True
    request_counter_name: str = "http_requests_total"
    request_histogram_name: str = "http_request_duration_seconds"
    write_timeout: float | None = None


@dataclass
class MiddlewareScenarioContext:
    """Shared state between steps in a middleware scenario."""

    log_storage: InMemoryLogStorage = field(default_factory=InMemoryLogStorage)
    metrics_storage: InMemoryMetricsStorage = field(
        default_factory=InMemoryMetricsStorage
    )
    app: Any = None
    request_capture: RequestCapture = field(default_factory=RequestCapture)
    config: MiddlewareConfig = field(default_factory=MiddlewareConfig)
    custom_app: Any = None
    endpoint_context_value: dict[str, Any] = field(default_factory=dict)
    concurrent_results: list[dict[str, Any]] = field(default_factory=list)
    wsgi_app: Any = None
    exception_raised: Exception | None = None
    storage_failure: bool = False
    storage_hang_seconds: float = 0


@pytest.fixture
def ctx() -> MiddlewareScenarioContext:
    """Fresh scenario context for each test."""
    clear_log_context()
    return MiddlewareScenarioContext()


# === Helper Functions ===


def run_async(coro: Any) -> Any:
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


async def read_logs(storage: InMemoryLogStorage) -> list[LogEntry]:
    """Read all logs from storage."""
    return [entry async for entry in storage.read()]


async def read_metrics(storage: InMemoryMetricsStorage) -> list[MetricSample]:
    """Read all metrics from storage."""
    return [sample async for sample in storage.read()]


async def simulate_request(
    ctx: MiddlewareScenarioContext,
    method: str = "GET",
    path: str = "/",
    headers: dict[str, str] | None = None,
) -> None:
    """Simulate an HTTP request through the ASGI middleware."""
    if headers is None:
        headers = {}

    scope: Scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
    }

    captured_status = 0
    captured_body = b""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        nonlocal captured_status, captured_body
        if message["type"] == "http.response.start":
            captured_status = message.get("status", 200)
        elif message["type"] == "http.response.body":
            captured_body += message.get("body", b"")

    try:
        await ctx.app(scope, receive, send)
        ctx.request_capture.status_code = captured_status
        ctx.request_capture.response_body = captured_body.decode()
    except Exception as e:
        ctx.request_capture.exception = e
        ctx.exception_raised = e
        raise


def create_test_app(
    ctx: MiddlewareScenarioContext,
    status_code: int = 200,
    raise_exception: Exception | None = None,
    app_logs: int = 0,
    delay_ms: float = 0,
) -> Any:
    """Create a test ASGI app with configurable behavior."""

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return

        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

        for i in range(app_logs):
            log_entry = LogEntry(
                timestamp=asyncio.get_event_loop().time(),
                level="INFO",
                message=f"Application log {i + 1}",
                attributes=get_log_context(),
            )
            await ctx.log_storage.write(log_entry)

        if raise_exception is not None:
            raise raise_exception

        await send(
            {"type": "http.response.start", "status": status_code, "headers": []}
        )
        await send({"type": "http.response.body", "body": b"OK"})

    return test_app


def log_matches_expected(log: LogEntry, expected: dict[str, str]) -> bool:
    """Check if a log entry matches expected attributes."""
    for key, value in expected.items():
        if key == "level" and log.level != value:
            return False
        if key == "method" and log.attributes.get("method") != value:
            return False
        if key == "path" and log.attributes.get("path") != value:
            return False
        if key == "status_code" and str(log.attributes.get("status_code")) != value:
            return False
    return True


# Re-export for convenience
__all__ = [
    "RequestCapture",
    "MiddlewareConfig",
    "MiddlewareScenarioContext",
    "ctx",
    "run_async",
    "read_logs",
    "read_metrics",
    "simulate_request",
    "create_test_app",
    "log_matches_expected",
    "ASGIObservabilityMiddleware",
    "InMemoryLogStorage",
    "InMemoryMetricsStorage",
    "LogEntry",
    "MetricSample",
    "Scope",
    "Receive",
    "Send",
    "get_log_context",
    "clear_log_context",
]
