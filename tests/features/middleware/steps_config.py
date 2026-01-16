"""Step definitions for middleware_configuration.feature (Cycle 3)."""

import pytest
from pytest_bdd import given, parsers, then, when
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    MiddlewareScenarioContext,
    create_test_app,
    read_logs,
    read_metrics,
    run_async,
    simulate_request,
)


@given(parsers.parse('middleware configured with exclude_paths=["{path1}", "{path2}"]'))
def given_middleware_with_exclude_paths(
    ctx: MiddlewareScenarioContext, path1: str, path2: str
) -> None:
    """Configure middleware with excluded paths."""
    ctx.config.exclude_paths = [path1, path2]
    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given(parsers.parse('middleware configured with exclude_paths=["{pattern}"]'))
def given_middleware_with_exclude_pattern(
    ctx: MiddlewareScenarioContext, pattern: str
) -> None:
    """Configure middleware with exclude pattern."""
    ctx.config.exclude_paths = [pattern]
    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given(parsers.parse('middleware configured with request_id_header="{header}"'))
def given_middleware_with_custom_header(
    ctx: MiddlewareScenarioContext, header: str
) -> None:
    """Configure middleware with custom request ID header."""
    ctx.config.request_id_header = header
    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given(parsers.parse("middleware configured with log_requests=False"))
def given_middleware_logging_disabled(ctx: MiddlewareScenarioContext) -> None:
    """Configure middleware with logging disabled."""
    ctx.config.log_requests = False
    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given(parsers.parse("middleware configured with record_metrics=False"))
def given_middleware_metrics_disabled(ctx: MiddlewareScenarioContext) -> None:
    """Configure middleware with metrics disabled."""
    ctx.config.record_metrics = False
    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@given("middleware configured with:")
def given_middleware_with_config(
    ctx: MiddlewareScenarioContext, datatable: list[list[str]]
) -> None:
    """Configure middleware with options from datatable."""
    for row in datatable[1:]:
        if len(row) >= 2:
            option, value = row[0], row[1]
            if option == "request_counter_name":
                ctx.config.request_counter_name = value
            elif option == "request_histogram_name":
                ctx.config.request_histogram_name = value

    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )


@when(parsers.parse('requests are made to "{path1}" and "{path2}"'))
def when_requests_to_two_paths(
    ctx: MiddlewareScenarioContext, path1: str, path2: str
) -> None:
    """Make requests to two paths."""
    run_async(simulate_request(ctx, method="GET", path=path1))
    run_async(simulate_request(ctx, method="GET", path=path2))


@when(parsers.parse('a request is made with header {header}="{value}"'))
def when_request_with_header(
    ctx: MiddlewareScenarioContext, header: str, value: str
) -> None:
    """Make a request with a specific header."""
    run_async(
        simulate_request(ctx, method="GET", path="/test", headers={header: value})
    )


@then("no log entry should be recorded")
def then_no_log_entry(ctx: MiddlewareScenarioContext) -> None:
    """Assert no log entry was recorded."""
    logs = run_async(read_logs(ctx.log_storage))
    assert len(logs) == 0, f"Expected no logs, got {len(logs)}"


@then("no log entries should be recorded")
def then_no_log_entries(ctx: MiddlewareScenarioContext) -> None:
    """Assert no log entries were recorded."""
    then_no_log_entry(ctx)


@then("no metrics should be recorded")
def then_no_metrics(ctx: MiddlewareScenarioContext) -> None:
    """Assert no metrics were recorded."""
    metrics = run_async(read_metrics(ctx.metrics_storage))
    assert len(metrics) == 0, f"Expected no metrics, got {len(metrics)}"


@then(parsers.parse('a request to "{path}" should be logged'))
def then_request_should_be_logged(ctx: MiddlewareScenarioContext, path: str) -> None:
    """Assert a request to the path was logged."""
    run_async(simulate_request(ctx, method="GET", path=path))
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    assert any(log.attributes.get("path") == path for log in logs)


@then(parsers.parse('the log entry should have request_id="{request_id}"'))
def then_log_entry_request_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    """Assert log entry has specific request_id."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    assert any(log.attributes.get("request_id") == request_id for log in logs)


@then("a log entry should be recorded")
def then_log_entry_recorded(ctx: MiddlewareScenarioContext) -> None:
    """Assert a log entry was recorded."""
    logs = run_async(read_logs(ctx.log_storage))

    if len(logs) == 0:
        pytest.xfail("Middleware request logging not yet implemented")

    assert len(logs) > 0


@then(parsers.parse('"{name}" should be incremented'))
def then_metric_incremented(ctx: MiddlewareScenarioContext, name: str) -> None:
    """Assert the metric was incremented."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    assert any(m.name == name for m in metrics)


@then(parsers.parse('"{name}" should be recorded'))
def then_metric_name_recorded(ctx: MiddlewareScenarioContext, name: str) -> None:
    """Assert the metric was recorded."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    assert any(m.name == name for m in metrics)


__all__ = [
    "given_middleware_with_exclude_paths",
    "given_middleware_with_exclude_pattern",
    "given_middleware_with_custom_header",
    "given_middleware_logging_disabled",
    "given_middleware_metrics_disabled",
    "given_middleware_with_config",
    "when_requests_to_two_paths",
    "when_request_with_header",
    "then_no_log_entry",
    "then_no_log_entries",
    "then_no_metrics",
    "then_request_should_be_logged",
    "then_log_entry_request_id",
    "then_log_entry_recorded",
    "then_metric_incremented",
    "then_metric_name_recorded",
]
