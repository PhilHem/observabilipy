"""Tests for ASGI middleware auto-instrumentation.

This module tests the ASGIObservabilityMiddleware class that wraps ASGI applications
to automatically capture request/response metrics and logs.
"""

from __future__ import annotations

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


# === Fixture Tests ===


@pytest.mark.tier(0)
@pytest.mark.tra("Adapter.ASGI.Fixtures.BasicApp")
def test_basic_asgi_app_fixture_returns_callable(basic_asgi_app):
    """basic_asgi_app fixture should return a callable ASGI application."""
    # Assert: Fixture should return a callable
    assert callable(basic_asgi_app)


@pytest.mark.tier(0)
@pytest.mark.tra("Adapter.ASGI.Fixtures.Scope")
def test_asgi_scope_fixture_returns_valid_scope(asgi_scope):
    """asgi_scope fixture should return factory creating valid scope dicts."""
    # Act: Create default scope
    scope = asgi_scope()

    # Assert: Scope should have required ASGI HTTP fields
    assert scope["type"] == "http"
    assert scope["method"] == "GET"
    assert scope["path"] == "/test"
    assert scope["query_string"] == b""
    assert scope["headers"] == []

    # Act: Create custom scope
    custom_scope = asgi_scope(method="POST", path="/custom")

    # Assert: Custom scope should respect parameters
    assert custom_scope["type"] == "http"
    assert custom_scope["method"] == "POST"
    assert custom_scope["path"] == "/custom"


@pytest.mark.tier(0)
@pytest.mark.tra("Adapter.ASGI.Fixtures.SendCapture")
@pytest.mark.asyncio
async def test_asgi_send_capture_records_messages(asgi_send_capture):
    """asgi_send_capture fixture should record ASGI messages."""
    # Arrange: Unpack fixture
    send, responses = asgi_send_capture

    # Act: Send two messages
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"OK"})

    # Assert: Responses should be recorded
    assert len(responses) == 2
    assert responses[0]["type"] == "http.response.start"
    assert responses[0]["status"] == 200
    assert responses[1]["type"] == "http.response.body"
    assert responses[1]["body"] == b"OK"


# === Query Parameter Parsing Tests ===


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.InvalidUTF8")
def test_parse_since_param_handles_invalid_utf8_bytes():
    """_parse_since_param should handle invalid UTF-8 bytes in query string."""
    from observabilipy.adapters.frameworks.asgi import _parse_since_param

    # Arrange: Simulate invalid UTF-8 bytes in query string that would be
    # decoded with errors='replace' to produce placeholder characters
    query_string = "since=\ufffd\ufffd".encode()  # Replacement chars
    params = __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs(
        query_string.decode("utf-8", errors="replace")
    )

    # Act: Parse the 'since' parameter
    result = _parse_since_param(params)

    # Assert: Should return default value (0.0) without raising
    assert isinstance(result, float)
    assert result == 0.0


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.InvalidUTF8")
def test_parse_level_param_handles_invalid_utf8_bytes():
    """_parse_level_param should handle invalid UTF-8 bytes in query string."""
    from observabilipy.adapters.frameworks.asgi import _parse_level_param

    # Arrange: Simulate invalid UTF-8 bytes in query string that would be
    # decoded with errors='replace' to produce placeholder characters
    query_string = "level=\ufffd\ufffd".encode()  # Replacement chars
    params = __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs(
        query_string.decode("utf-8", errors="replace")
    )

    # Act: Parse the 'level' parameter
    result = _parse_level_param(params)

    # Assert: Should return None without raising
    assert result is None


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.Parser")
def test_parse_query_params_extracts_all_params():
    """_parse_query_params should extract all parameters from scope query_string."""
    from observabilipy.adapters.frameworks.asgi import _parse_query_params

    # Arrange: Create scope with query string
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"since=12345.0&level=INFO&other=value",
        "headers": [],
    }

    # Act: Parse query parameters
    result = _parse_query_params(scope)

    # Assert: Should return dict with all parameters
    assert result == {"since": ["12345.0"], "level": ["INFO"], "other": ["value"]}


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.Parser")
def test_parse_query_params_handles_missing_query_string():
    """_parse_query_params should handle scope without query_string key."""
    from observabilipy.adapters.frameworks.asgi import _parse_query_params

    # Arrange: Create scope without query_string key
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }

    # Act: Parse query parameters
    result = _parse_query_params(scope)

    # Assert: Should return empty dict
    assert result == {}


# === _send_response Helper Tests ===


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.SendResponse.Headers")
@pytest.mark.asyncio
async def test_send_response_sends_correct_headers():
    """_send_response sends http.response.start with correct status."""
    from observabilipy.adapters.frameworks.asgi import _send_response

    # Arrange: Create send capture
    responses: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        responses.append(message)

    # Act: Send response with specific status and content type
    await _send_response(send, 201, "text/plain", "test body")

    # Assert: Should send http.response.start with correct headers
    assert len(responses) == 2
    assert responses[0]["type"] == "http.response.start"
    assert responses[0]["status"] == 201
    assert responses[0]["headers"] == [(b"content-type", b"text/plain")]


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.SendResponse.Body")
@pytest.mark.asyncio
async def test_send_response_sends_body_as_bytes():
    """_send_response should send http.response.body with body encoded as bytes."""
    from observabilipy.adapters.frameworks.asgi import _send_response

    # Arrange: Create send capture
    responses: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        responses.append(message)

    # Act: Send response with string body
    await _send_response(send, 200, "application/json", "{'key': 'value'}")

    # Assert: Should send http.response.body with encoded body
    assert len(responses) == 2
    assert responses[1]["type"] == "http.response.body"
    assert responses[1]["body"] == b"{'key': 'value'}"
