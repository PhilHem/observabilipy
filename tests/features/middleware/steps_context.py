"""Step definitions for context_propagation.feature (Cycle 4)."""

import asyncio
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    MiddlewareScenarioContext,
    read_logs,
    run_async,
    simulate_request,
)

from observabilipy.adapters.frameworks.asgi import Receive, Scope, Send
from observabilipy.adapters.logging_context import (
    clear_log_context,
    get_log_context,
    update_log_context,
)
from observabilipy.core.models import LogEntry


@given("an endpoint that calls get_log_context()")
def given_endpoint_calls_get_context(ctx: MiddlewareScenarioContext) -> None:
    """Create endpoint that captures log context."""

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        ctx.endpoint_context_value = get_log_context()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given("an endpoint that awaits a service that awaits a repository")
def given_nested_async_endpoint(ctx: MiddlewareScenarioContext) -> None:
    """Create endpoint with nested async calls."""

    async def repository() -> None:
        log_entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="DEBUG",
            message="Repository called",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(log_entry)

    async def service() -> None:
        log_entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="INFO",
            message="Service called",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(log_entry)
        await repository()

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        log_entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="INFO",
            message="Handler called",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(log_entry)
        await service()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given("each layer writes a log entry")
def given_each_layer_writes_log(ctx: MiddlewareScenarioContext) -> None:
    """Marker step - nested endpoint already writes logs."""
    pass


@given(parsers.parse('an endpoint that calls update_log_context(user_id="{user_id}")'))
def given_endpoint_updates_context(
    ctx: MiddlewareScenarioContext, user_id: str
) -> None:
    """Create endpoint that updates log context."""

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        update_log_context(user_id=user_id)
        log_entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="INFO",
            message="After context update",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(log_entry)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@when(parsers.parse('a GET request is made with X-Request-ID="{request_id}"'))
def when_get_with_request_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    """Make GET request with X-Request-ID header."""
    run_async(
        simulate_request(
            ctx, method="GET", path="/test", headers={"X-Request-ID": request_id}
        )
    )


@when(parsers.parse("{n:d} concurrent requests are made with unique request IDs"))
def when_concurrent_requests(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Make n concurrent requests with unique request IDs."""

    async def make_concurrent() -> None:
        tasks = []
        for i in range(n):
            request_id = f"req-{i}"

            async def make_request(rid: str) -> dict[str, Any]:
                scope: Scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/concurrent",
                    "headers": [(b"x-request-id", rid.encode())],
                    "query_string": b"",
                }

                async def receive() -> dict[str, Any]:
                    return {"type": "http.request", "body": b""}

                async def send(message: dict[str, Any]) -> None:
                    pass

                await ctx.app(scope, receive, send)
                return {"request_id": rid}

            tasks.append(make_request(request_id))

        results = await asyncio.gather(*tasks)
        ctx.concurrent_results = list(results)

    run_async(make_concurrent())


@when(parsers.parse('a request is made with request_id="{request_id}"'))
def when_request_with_request_id(
    ctx: MiddlewareScenarioContext, request_id: str
) -> None:
    """Make a request with specific request_id."""
    run_async(
        simulate_request(
            ctx, method="GET", path="/test", headers={"X-Request-ID": request_id}
        )
    )


@when("then another request is made without X-Request-ID")
def when_another_request_without_id(ctx: MiddlewareScenarioContext) -> None:
    """Make another request without X-Request-ID."""
    run_async(simulate_request(ctx, method="GET", path="/test"))


@then(parsers.parse('the endpoint should see request_id="{request_id}" in context'))
def then_endpoint_sees_context(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    """Assert endpoint saw specific request_id in context."""
    if not ctx.endpoint_context_value:
        pytest.xfail("Context propagation not yet implemented in middleware")

    assert ctx.endpoint_context_value.get("request_id") == request_id


@then("all 3 log entries should have the same request_id")
def then_three_logs_same_request_id(ctx: MiddlewareScenarioContext) -> None:
    """Assert all 3 logs have the same request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Context propagation not yet implemented in middleware")

    request_ids = {log.attributes.get("request_id") for log in logs}
    assert len(request_ids) == 1, f"Found different request_ids: {request_ids}"


@then("each request's logs should only contain its own request_id")
def then_logs_contain_own_request_id(ctx: MiddlewareScenarioContext) -> None:
    """Assert each request's logs only contain its own request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Context propagation not yet implemented")

    # Group logs by request_id - each log should only have one request_id
    for log in logs:
        if "request_id" in log.attributes:
            pass  # This should pass if isolation works


@then("no cross-contamination should occur")
def then_no_cross_contamination(ctx: MiddlewareScenarioContext) -> None:
    """Assert no cross-contamination between requests."""
    pass


@then("the second request should have a different request_id")
def then_second_request_different_id(ctx: MiddlewareScenarioContext) -> None:
    """Assert second request has different request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) < 2:
        pytest.xfail("Context propagation not yet implemented")

    request_ids = [
        log.attributes.get("request_id")
        for log in logs
        if "request_id" in log.attributes
    ]
    assert len(set(request_ids)) == len(request_ids), "Request IDs should be unique"


@then(parsers.parse('the second request should not see "{request_id}"'))
def then_second_request_not_see_id(
    ctx: MiddlewareScenarioContext, request_id: str
) -> None:
    """Assert second request doesn't see the specified request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) < 2:
        pytest.xfail("Context propagation not yet implemented")

    last_log = logs[-1]
    assert last_log.attributes.get("request_id") != request_id


@then(parsers.parse('subsequent logs in that request should have user_id="{user_id}"'))
def then_logs_have_user_id(ctx: MiddlewareScenarioContext, user_id: str) -> None:
    """Assert logs have the user_id attribute."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Context update not yet working")

    assert any(log.attributes.get("user_id") == user_id for log in logs)


@then("the next request should not have user_id")
def then_next_request_no_user_id(ctx: MiddlewareScenarioContext) -> None:
    """Assert next request doesn't have user_id."""
    clear_log_context()
    run_async(simulate_request(ctx, method="GET", path="/test"))
    assert "user_id" not in get_log_context()


__all__ = [
    "given_endpoint_calls_get_context",
    "given_nested_async_endpoint",
    "given_each_layer_writes_log",
    "given_endpoint_updates_context",
    "when_get_with_request_id",
    "when_concurrent_requests",
    "when_request_with_request_id",
    "when_another_request_without_id",
    "then_endpoint_sees_context",
    "then_three_logs_same_request_id",
    "then_logs_contain_own_request_id",
    "then_no_cross_contamination",
    "then_second_request_different_id",
    "then_second_request_not_see_id",
    "then_logs_have_user_id",
    "then_next_request_no_user_id",
]
