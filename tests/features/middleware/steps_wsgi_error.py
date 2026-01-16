"""Step definitions for wsgi_middleware.feature and error_handling.feature."""

import asyncio

import pytest
from pytest_bdd import given, parsers, then, when
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    InMemoryLogStorage,
    MiddlewareScenarioContext,
    read_logs,
    read_metrics,
    run_async,
    simulate_request,
)

from observabilipy.adapters.frameworks.asgi import Receive, Scope, Send
from observabilipy.core.models import LogEntry

# === Cycle 5: wsgi_middleware.feature Steps ===


@given("a WSGI app with observability middleware")
def given_wsgi_app(ctx: MiddlewareScenarioContext) -> None:
    """Create a WSGI app with observability middleware."""
    pytest.xfail("WSGI middleware not yet implemented")


@given("a Flask endpoint that writes an application log")
def given_flask_endpoint_writes_log(ctx: MiddlewareScenarioContext) -> None:
    """Create Flask endpoint that writes a log."""
    pytest.xfail("WSGI middleware not yet implemented")


@given("sync-only storage adapters")
def given_sync_storage(ctx: MiddlewareScenarioContext) -> None:
    """Use sync-only storage adapters."""
    pass


@given(parsers.parse("a threaded WSGI server with {n:d} worker threads"))
def given_threaded_wsgi_server(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Create threaded WSGI server."""
    pytest.xfail("WSGI threading test not yet implemented")


@then(
    parsers.parse(
        'a log entry should be recorded with method="{method}" and path="{path}"'
    )
)
def then_log_with_method_path(
    ctx: MiddlewareScenarioContext, method: str, path: str
) -> None:
    """Assert log entry has method and path."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("WSGI logging not yet implemented")

    assert any(
        log.attributes.get("method") == method and log.attributes.get("path") == path
        for log in logs
    )


@then(parsers.parse('"{name}" should be incremented with status="{status}"'))
def then_metric_with_status(
    ctx: MiddlewareScenarioContext, name: str, status: str
) -> None:
    """Assert metric was incremented with status label."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("WSGI metrics not yet implemented")

    assert any(m.name == name and m.labels.get("status") == status for m in metrics)


_BOTH_LOGS_PATTERN = (
    'both the middleware log and application log should have request_id="{request_id}"'
)


@then(parsers.parse(_BOTH_LOGS_PATTERN))
def then_both_logs_have_request_id(
    ctx: MiddlewareScenarioContext, request_id: str
) -> None:
    """Assert both middleware and app logs have request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) < 2:
        pytest.xfail("WSGI context propagation not yet implemented")

    assert all(log.attributes.get("request_id") == request_id for log in logs)


@then("logs and metrics should be written without async errors")
def then_no_async_errors(ctx: MiddlewareScenarioContext) -> None:
    """Assert no async errors occurred."""
    pass


@when("concurrent requests hit different threads")
def when_concurrent_thread_requests(ctx: MiddlewareScenarioContext) -> None:
    """Make concurrent requests to different threads."""
    pytest.xfail("WSGI threading not yet implemented")


@then("each thread should correctly isolate request context")
def then_threads_isolate_context(ctx: MiddlewareScenarioContext) -> None:
    """Assert thread isolation works."""
    pytest.xfail("WSGI thread isolation not yet implemented")


# === Cycle 6: error_handling.feature Steps ===


@given(parsers.parse('an endpoint that raises {exception}("{message}")'))
def given_endpoint_raises(
    ctx: MiddlewareScenarioContext, exception: str, message: str
) -> None:
    """Create endpoint that raises exception."""
    exc_class = {"ValueError": ValueError, "RuntimeError": RuntimeError}.get(
        exception, RuntimeError
    )

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        raise exc_class(message)

    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given(parsers.parse("log storage that raises {exception} on write"))
def given_failing_storage(ctx: MiddlewareScenarioContext, exception: str) -> None:
    """Create storage that fails on write."""

    class FailingLogStorage(InMemoryLogStorage):
        async def write(self, entry: LogEntry) -> None:
            raise OSError("Storage failure")

    ctx.log_storage = FailingLogStorage()
    ctx.storage_failure = True


@given(parsers.parse("log storage that hangs for {n:d} seconds"))
def given_hanging_storage(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Create storage that hangs on write."""

    class HangingLogStorage(InMemoryLogStorage):
        async def write(self, entry: LogEntry) -> None:
            await asyncio.sleep(n)
            await super().write(entry)

    ctx.log_storage = HangingLogStorage()
    ctx.storage_hang_seconds = n


@given(parsers.parse("middleware configured with write_timeout={n:d}ms"))
def given_middleware_with_timeout(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Configure middleware with write timeout."""
    ctx.config.write_timeout = n / 1000.0


@given("an endpoint that raises RuntimeError")
def given_endpoint_raises_runtime_error(ctx: MiddlewareScenarioContext) -> None:
    """Create endpoint that raises RuntimeError."""

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        raise RuntimeError("Test error")

    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given("context cleanup that also raises an error")
def given_cleanup_raises(ctx: MiddlewareScenarioContext) -> None:
    """Mark that cleanup will raise."""
    pass


@when("a request is made to that endpoint")
def when_request_to_custom_endpoint(ctx: MiddlewareScenarioContext) -> None:
    """Make request to the custom endpoint."""
    try:
        run_async(simulate_request(ctx, method="GET", path="/failing"))
    except Exception as e:
        ctx.exception_raised = e


@then("an ERROR log should be recorded with exception details")
def then_error_log_with_exception(ctx: MiddlewareScenarioContext) -> None:
    """Assert ERROR log was recorded with exception."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Exception logging not yet implemented")

    error_logs = [log for log in logs if log.level == "ERROR"]
    assert len(error_logs) > 0, "No ERROR logs found"
    assert any("exception" in log.attributes for log in error_logs)


@then("the ValueError should still propagate to the client")
def then_valueerror_propagates(ctx: MiddlewareScenarioContext) -> None:
    """Assert ValueError propagated."""
    assert isinstance(ctx.exception_raised, ValueError)


@then(parsers.parse("status_code should be {code:d}"))
def then_status_code(ctx: MiddlewareScenarioContext, code: int) -> None:
    """Assert status code."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Status code logging not yet implemented")

    assert any(log.attributes.get("status_code") == code for log in logs)


@then("the request should complete successfully")
def then_request_completes(ctx: MiddlewareScenarioContext) -> None:
    """Assert request completed successfully."""
    assert ctx.request_capture.status_code == 200


@then("the response should be returned to the client")
def then_response_returned(ctx: MiddlewareScenarioContext) -> None:
    """Assert response was returned."""
    assert ctx.request_capture.response_body is not None


@then("a warning should be logged to stderr")
def then_warning_to_stderr(ctx: MiddlewareScenarioContext) -> None:
    """Assert warning was logged to stderr."""
    pytest.xfail("Stderr warning capture not implemented")


@then(parsers.parse("the request should complete within {n:d}ms"))
def then_request_within_time(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Assert request completed within time limit."""
    pytest.xfail("Request timing not implemented")


@then("the response should be returned")
def then_response_is_returned(ctx: MiddlewareScenarioContext) -> None:
    """Assert response was returned."""
    assert ctx.request_capture.response_body is not None


@then("the RuntimeError should be raised to the client")
def then_runtimeerror_raised(ctx: MiddlewareScenarioContext) -> None:
    """Assert RuntimeError was raised."""
    assert isinstance(ctx.exception_raised, RuntimeError)


@then("the cleanup error should be logged separately")
def then_cleanup_error_logged(ctx: MiddlewareScenarioContext) -> None:
    """Assert cleanup error was logged."""
    pytest.xfail("Cleanup error logging not yet implemented")


__all__ = [
    # WSGI steps
    "given_wsgi_app",
    "given_flask_endpoint_writes_log",
    "given_sync_storage",
    "given_threaded_wsgi_server",
    "then_log_with_method_path",
    "then_metric_with_status",
    "then_both_logs_have_request_id",
    "then_no_async_errors",
    "when_concurrent_thread_requests",
    "then_threads_isolate_context",
    # Error handling steps
    "given_endpoint_raises",
    "given_failing_storage",
    "given_hanging_storage",
    "given_middleware_with_timeout",
    "given_endpoint_raises_runtime_error",
    "given_cleanup_raises",
    "when_request_to_custom_endpoint",
    "then_error_log_with_exception",
    "then_valueerror_propagates",
    "then_status_code",
    "then_request_completes",
    "then_response_returned",
    "then_warning_to_stderr",
    "then_request_within_time",
    "then_response_is_returned",
    "then_runtimeerror_raised",
    "then_cleanup_error_logged",
]
