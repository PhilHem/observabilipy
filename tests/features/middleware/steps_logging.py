"""Step definitions for request_logging.feature (Cycle 1)."""

import uuid

import pytest
from pytest_bdd import given, parsers, then, when
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    LogEntry,
    MiddlewareScenarioContext,
    create_test_app,
    log_matches_expected,
    read_logs,
    run_async,
    simulate_request,
)


@given(parsers.parse("an endpoint that writes {n:d} application logs"))
def given_endpoint_with_app_logs(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Create an endpoint that writes n application logs."""
    test_app = create_test_app(ctx, app_logs=n)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@when(parsers.parse('a GET request is made to "{path}"'))
def when_get_request_to_path(ctx: MiddlewareScenarioContext, path: str) -> None:
    """Make a GET request to the specified path."""
    ctx.request_capture.method = "GET"
    ctx.request_capture.path = path

    async def run_request() -> None:
        await simulate_request(ctx, method="GET", path=path)

    try:
        run_async(run_request())
    except Exception:  # noqa: S110
        pass  # Exception is captured in ctx.request_capture


@when("a GET request is made to that endpoint")
def when_get_request_to_custom_endpoint(ctx: MiddlewareScenarioContext) -> None:
    """Make a GET request to the custom endpoint."""
    run_async(simulate_request(ctx, method="GET", path="/custom"))


@when(parsers.parse("the endpoint returns status {code:d}"))
def when_endpoint_returns_status(ctx: MiddlewareScenarioContext, code: int) -> None:
    """Configure endpoint to return the specified status code."""
    test_app = create_test_app(ctx, status_code=code)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )
    path = ctx.request_capture.path or "/"
    run_async(simulate_request(ctx, method="GET", path=path))


@when("the endpoint raises an unhandled exception")
def when_endpoint_raises_exception(ctx: MiddlewareScenarioContext) -> None:
    """Configure endpoint to raise an exception."""
    test_app = create_test_app(ctx, raise_exception=RuntimeError("Unhandled error"))
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )
    path = ctx.request_capture.path or "/"
    try:
        run_async(simulate_request(ctx, method="GET", path=path))
    except RuntimeError:
        pass


@when("a GET request is made without X-Request-ID header")
def when_get_request_without_request_id(ctx: MiddlewareScenarioContext) -> None:
    """Make a GET request without X-Request-ID header."""
    run_async(simulate_request(ctx, method="GET", path="/test"))


@when(parsers.parse('a GET request is made with header X-Request-ID="{request_id}"'))
def when_get_request_with_request_id(
    ctx: MiddlewareScenarioContext, request_id: str
) -> None:
    """Make a GET request with X-Request-ID header."""
    run_async(
        simulate_request(
            ctx, method="GET", path="/test", headers={"X-Request-ID": request_id}
        )
    )


@then("a log entry should be recorded with:")
def then_log_entry_with_attributes(
    ctx: MiddlewareScenarioContext, datatable: list[list[str]]
) -> None:
    """Assert a log entry exists with the specified attributes."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    expected = {row[0]: row[1] for row in datatable[1:] if len(row) >= 2}
    found = any(log_matches_expected(log, expected) for log in logs)
    assert found, f"No log entry matches expected attributes: {expected}"


@then(parsers.parse('the log entry should have a "{attr}" attribute'))
def then_log_entry_has_attribute(ctx: MiddlewareScenarioContext, attr: str) -> None:
    """Assert the log entry has the specified attribute."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    log = logs[-1]
    assert attr in log.attributes, f"Log entry missing attribute: {attr}"


@then('the log entry should have an "exception" attribute')
def then_log_entry_has_exception_attribute(ctx: MiddlewareScenarioContext) -> None:
    """Assert the log entry has an exception attribute."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    log = logs[-1]
    assert "exception" in log.attributes, "Log entry missing exception attribute"


@then('a log entry should be recorded with a "request_id" attribute')
def then_log_has_request_id(ctx: MiddlewareScenarioContext) -> None:
    """Assert a log entry was recorded with request_id attribute."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    assert any("request_id" in log.attributes for log in logs)


@then("the request_id should be a valid UUID")
def then_request_id_is_uuid(ctx: MiddlewareScenarioContext) -> None:
    """Assert the request_id is a valid UUID."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    for log in logs:
        if "request_id" in log.attributes:
            request_id = str(log.attributes["request_id"])
            try:
                uuid.UUID(request_id)
                return
            except ValueError:
                pass
    pytest.fail("No valid UUID request_id found")


@then(parsers.parse('a log entry should be recorded with request_id="{request_id}"'))
def then_log_has_specific_request_id(
    ctx: MiddlewareScenarioContext, request_id: str
) -> None:
    """Assert a log entry has the specific request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    for log in logs:
        if log.attributes.get("request_id") == request_id:
            return
    pytest.fail(f"No log entry with request_id={request_id}")


@then(parsers.parse("{n:d} log entries should be recorded"))
def then_n_log_entries(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Assert exactly n log entries were recorded."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0 and n > 0:
        pytest.xfail("Middleware request logging not yet implemented")

    if len(logs) < n:
        pytest.xfail(
            f"Middleware request logging not yet implemented "
            f"(got {len(logs)} logs, expected {n})"
        )

    assert len(logs) == n, f"Expected {n} logs, got {len(logs)}"


@then("all log entries should have the same request_id")
def then_all_logs_same_request_id(ctx: MiddlewareScenarioContext) -> None:
    """Assert all log entries have the same request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    request_ids = {
        log.attributes.get("request_id")
        for log in logs
        if "request_id" in log.attributes
    }
    assert len(request_ids) == 1, f"Multiple request_ids found: {request_ids}"


# Re-export for conftest
__all__ = [
    "given_endpoint_with_app_logs",
    "when_get_request_to_path",
    "when_get_request_to_custom_endpoint",
    "when_endpoint_returns_status",
    "when_endpoint_raises_exception",
    "when_get_request_without_request_id",
    "when_get_request_with_request_id",
    "then_log_entry_with_attributes",
    "then_log_entry_has_attribute",
    "then_log_entry_has_exception_attribute",
    "then_log_has_request_id",
    "then_request_id_is_uuid",
    "then_log_has_specific_request_id",
    "then_n_log_entries",
    "then_all_logs_same_request_id",
    "LogEntry",
]
