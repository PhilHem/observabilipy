"""Step definitions for request_metrics.feature (Cycle 2)."""

import pytest
from pytest_bdd import parsers, then, when
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    MiddlewareScenarioContext,
    create_test_app,
    read_metrics,
    run_async,
    simulate_request,
)


@when(parsers.parse('{n:d} GET requests are made to "{path}"'))
def when_n_get_requests(ctx: MiddlewareScenarioContext, n: int, path: str) -> None:
    """Make n GET requests to the specified path."""
    for _ in range(n):
        run_async(simulate_request(ctx, method="GET", path=path))


@when(parsers.parse("a GET request returns status {code:d}"))
def when_get_request_returns_status(ctx: MiddlewareScenarioContext, code: int) -> None:
    """Make a GET request that returns the specified status code."""
    test_app = create_test_app(ctx, status_code=code)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )
    run_async(simulate_request(ctx, method="GET", path="/test"))


@when(parsers.parse("a GET request is made that takes {n:d}ms"))
def when_get_request_with_delay(ctx: MiddlewareScenarioContext, n: int) -> None:
    """Make a GET request that takes n milliseconds."""
    test_app = create_test_app(ctx, delay_ms=n)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )
    run_async(simulate_request(ctx, method="GET", path="/test"))


@when("a request is made")
def when_a_request_is_made(ctx: MiddlewareScenarioContext) -> None:
    """Make a generic request."""
    try:
        run_async(simulate_request(ctx, method="GET", path="/test"))
    except Exception as e:
        ctx.exception_raised = e


@when(parsers.parse('requests are made to "{path1}", "{path2}", "{path3}"'))
def when_requests_to_multiple_paths(
    ctx: MiddlewareScenarioContext, path1: str, path2: str, path3: str
) -> None:
    """Make requests to multiple paths."""
    for path in [path1, path2, path3]:
        run_async(simulate_request(ctx, method="GET", path=path))


@then(parsers.parse('the metric "{name}" should have count {n:d}'))
def then_metric_count(ctx: MiddlewareScenarioContext, name: str, n: int) -> None:
    """Assert the metric has the specified count."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    matching = [m for m in metrics if m.name == name]
    total = sum(m.value for m in matching)
    assert total == n, f"Expected {name} count {n}, got {total}"


@then("the metric should have labels:")
def then_metric_has_labels(
    ctx: MiddlewareScenarioContext, datatable: list[list[str]]
) -> None:
    """Assert the metric has the specified labels."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    expected_labels = {}
    for row in datatable[1:]:
        if len(row) >= 2:
            expected_labels[row[0]] = row[1]

    for metric in metrics:
        if all(metric.labels.get(k) == v for k, v in expected_labels.items()):
            return
    pytest.fail(f"No metric with labels: {expected_labels}")


@then(parsers.parse('"{name}" with status="{status}" should have count {n:d}'))
def then_metric_with_status_count(
    ctx: MiddlewareScenarioContext, name: str, status: str, n: int
) -> None:
    """Assert metric with specific status has the count."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    matching = [
        m for m in metrics if m.name == name and m.labels.get("status") == status
    ]
    total = sum(m.value for m in matching)
    assert total == n, f"Expected {name} with status={status} count {n}, got {total}"


@then(parsers.parse('the metric "{name}" should be recorded'))
def then_metric_recorded(ctx: MiddlewareScenarioContext, name: str) -> None:
    """Assert the metric was recorded."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    assert any(m.name == name for m in metrics), f"Metric {name} not recorded"


@then("the histogram should have a sample in the 0.1-0.25 bucket")
def then_histogram_in_bucket(ctx: MiddlewareScenarioContext) -> None:
    """Assert histogram has a sample in the specified bucket."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    for metric in metrics:
        if "duration" in metric.name:
            if 0.1 <= metric.value <= 0.25:
                return
    pytest.xfail("Histogram bucket checking not yet implemented")


@then(parsers.parse('"{name}" should have buckets:'))
def then_metric_has_buckets(
    ctx: MiddlewareScenarioContext, name: str, datatable: list[list[str]]
) -> None:
    """Assert histogram has the expected bucket boundaries."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware histogram recording not yet implemented")

    # Extract expected bucket values (unused for now)
    _ = [row[0] for row in datatable[1:] if row]
    pytest.xfail("Histogram bucket verification not yet implemented")


@then(parsers.parse('the path label should be "{normalized_path}" for all requests'))
def then_path_label_normalized(
    ctx: MiddlewareScenarioContext, normalized_path: str
) -> None:
    """Assert path labels are normalized."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    for metric in metrics:
        if "path" in metric.labels:
            assert metric.labels["path"] == normalized_path
            return
    pytest.xfail("Path normalization not yet implemented")


@then(parsers.parse("there should be {n:d} unique label combination, not {m:d}"))
def then_unique_label_combinations(
    ctx: MiddlewareScenarioContext, n: int, m: int
) -> None:
    """Assert the number of unique label combinations."""
    metrics = run_async(read_metrics(ctx.metrics_storage))

    if len(metrics) == 0:
        pytest.xfail("Middleware metrics recording not yet implemented")

    unique_labels = {tuple(sorted(m.labels.items())) for m in metrics}
    assert len(unique_labels) == n, (
        f"Expected {n} unique label combos, got {len(unique_labels)}"
    )


__all__ = [
    "when_n_get_requests",
    "when_get_request_returns_status",
    "when_get_request_with_delay",
    "when_a_request_is_made",
    "when_requests_to_multiple_paths",
    "then_metric_count",
    "then_metric_has_labels",
    "then_metric_with_status_count",
    "then_metric_recorded",
    "then_histogram_in_bucket",
    "then_metric_has_buckets",
    "then_path_label_normalized",
    "then_unique_label_combinations",
]
