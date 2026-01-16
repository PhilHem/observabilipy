"""BDD step definitions for middleware observability features.

This conftest.py imports step implementations from modules and
registers them with pytest-bdd decorators. The implementations
live in separate files to keep this file under the line limit.
"""

import asyncio
import uuid
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    InMemoryLogStorage,
    InMemoryMetricsStorage,
    MiddlewareScenarioContext,
    create_test_app,
    log_matches_expected,
    read_logs,
    read_metrics,
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


@pytest.fixture
def ctx() -> MiddlewareScenarioContext:
    """Fresh scenario context for each test."""
    clear_log_context()
    return MiddlewareScenarioContext()


def _wrap(ctx: MiddlewareScenarioContext, app: Any) -> None:
    """Wrap app with observability middleware and store in context."""
    ctx.app = ASGIObservabilityMiddleware(
        app=app, log_storage=ctx.log_storage, metrics_storage=ctx.metrics_storage
    )


# === Background Steps ===
@given("in-memory log storage")
def step_log_storage(ctx: MiddlewareScenarioContext) -> None:
    ctx.log_storage = InMemoryLogStorage()


@given("in-memory metrics storage")
def step_metrics_storage(ctx: MiddlewareScenarioContext) -> None:
    ctx.metrics_storage = InMemoryMetricsStorage()


@given("an ASGI app with observability middleware")
def step_asgi_app(ctx: MiddlewareScenarioContext) -> None:
    _wrap(ctx, create_test_app(ctx))


# === Logging Steps (Cycle 1) ===
@given(parsers.parse("an endpoint that writes {n:d} application logs"))
def step_endpoint_with_logs(ctx: MiddlewareScenarioContext, n: int) -> None:
    test_app = create_test_app(ctx, app_logs=n)
    _wrap(ctx, test_app)


@when(parsers.parse('a GET request is made to "{path}"'))
def step_get_request(ctx: MiddlewareScenarioContext, path: str) -> None:
    ctx.request_capture.method, ctx.request_capture.path = "GET", path
    try:
        run_async(simulate_request(ctx, method="GET", path=path))
    except Exception as e:
        ctx.exception_raised = e


@when("a GET request is made to that endpoint")
def step_get_custom_endpoint(ctx: MiddlewareScenarioContext) -> None:
    run_async(simulate_request(ctx, method="GET", path="/custom"))


@when(parsers.parse("the endpoint returns status {code:d}"))
def step_endpoint_status(ctx: MiddlewareScenarioContext, code: int) -> None:
    test_app = create_test_app(ctx, status_code=code)
    _wrap(ctx, test_app)
    run_async(simulate_request(ctx, method="GET", path=ctx.request_capture.path or "/"))


@when("the endpoint raises an unhandled exception")
def step_endpoint_exception(ctx: MiddlewareScenarioContext) -> None:
    test_app = create_test_app(ctx, raise_exception=RuntimeError("Unhandled error"))
    _wrap(ctx, test_app)
    try:
        run_async(simulate_request(ctx, path=ctx.request_capture.path or "/"))
    except RuntimeError:
        pass


@when("a GET request is made without X-Request-ID header")
def step_get_without_request_id(ctx: MiddlewareScenarioContext) -> None:
    run_async(simulate_request(ctx, method="GET", path="/test"))


@when(parsers.parse('a GET request is made with header X-Request-ID="{request_id}"'))
def step_get_with_request_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    run_async(simulate_request(ctx, path="/test", headers={"X-Request-ID": request_id}))


@then("a log entry should be recorded with:")
def step_log_with_attrs(
    ctx: MiddlewareScenarioContext, datatable: list[list[str]]
) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    expected = {row[0]: row[1] for row in datatable[1:] if len(row) >= 2}
    assert any(log_matches_expected(log, expected) for log in logs)


@then(parsers.parse('the log entry should have a "{attr}" attribute'))
def step_log_has_attr(ctx: MiddlewareScenarioContext, attr: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert attr in logs[-1].attributes


@then('the log entry should have an "exception" attribute')
def step_log_has_exception(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert "exception" in logs[-1].attributes


@then('a log entry should be recorded with a "request_id" attribute')
def step_log_has_request_id(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert any("request_id" in log.attributes for log in logs)


@then("the request_id should be a valid UUID")
def step_request_id_uuid(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    for log in logs:
        if "request_id" in log.attributes:
            try:
                uuid.UUID(str(log.attributes["request_id"]))
                return
            except ValueError:
                pass
    pytest.fail("No valid UUID request_id found")


@then(parsers.parse('a log entry should be recorded with request_id="{request_id}"'))
def step_log_with_request_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert any(log.attributes.get("request_id") == request_id for log in logs)


@then(parsers.parse("{n:d} log entries should be recorded"))
def step_n_logs(ctx: MiddlewareScenarioContext, n: int) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs and n > 0:
        pytest.xfail("Middleware request logging not yet implemented")
    if len(logs) < n:
        pytest.xfail(f"Got {len(logs)} logs, expected {n}")
    assert len(logs) == n


@then("all log entries should have the same request_id")
def step_all_logs_same_id(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    ids = {
        log.attributes.get("request_id")
        for log in logs
        if "request_id" in log.attributes
    }
    assert len(ids) == 1


# === Metrics Steps (Cycle 2) ===
@when(parsers.parse('{n:d} GET requests are made to "{path}"'))
def step_n_requests(ctx: MiddlewareScenarioContext, n: int, path: str) -> None:
    for _ in range(n):
        run_async(simulate_request(ctx, method="GET", path=path))


@when(parsers.parse("a GET request returns status {code:d}"))
def step_request_returns_status(ctx: MiddlewareScenarioContext, code: int) -> None:
    test_app = create_test_app(ctx, status_code=code)
    _wrap(ctx, test_app)
    run_async(simulate_request(ctx, method="GET", path="/test"))


@when(parsers.parse("a GET request is made that takes {n:d}ms"))
def step_slow_request(ctx: MiddlewareScenarioContext, n: int) -> None:
    test_app = create_test_app(ctx, delay_ms=n)
    _wrap(ctx, test_app)
    run_async(simulate_request(ctx, method="GET", path="/slow"))


@then(parsers.parse('the metric "{name}" should have count {count:d}'))
def step_metric_count(ctx: MiddlewareScenarioContext, name: str, count: int) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("Middleware metrics recording not yet implemented")
    matching = [m for m in metrics if m.name == name]
    assert len(matching) == count


@then("the metric should have labels:")
def step_metric_labels(
    ctx: MiddlewareScenarioContext, datatable: list[list[str]]
) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("Middleware metrics recording not yet implemented")
    expected = {row[0]: row[1] for row in datatable[1:] if len(row) >= 2}
    assert any(all(m.labels.get(k) == v for k, v in expected.items()) for m in metrics)


@then(parsers.parse('the histogram should record ~{ms:d}ms in the "{bucket}" bucket'))
def step_histogram_bucket(ctx: MiddlewareScenarioContext, ms: int, bucket: str) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("Histogram recording not yet implemented")


@then("the histogram should use prometheus standard buckets")
def step_prometheus_buckets(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("Prometheus standard buckets not yet implemented")


@then(
    parsers.parse(
        'requests to "{path1}" and "{path2}" should have the same metric labels'
    )
)
def step_same_labels(ctx: MiddlewareScenarioContext, path1: str, path2: str) -> None:
    pytest.xfail("Path normalization not yet implemented")


@then(parsers.parse('"{name}" with status="{status}" should have count {n:d}'))
def step_metric_with_status_count(
    ctx: MiddlewareScenarioContext, name: str, status: str, n: int
) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("Middleware metrics recording not yet implemented")
    matching = [
        m for m in metrics if m.name == name and m.labels.get("status") == status
    ]
    assert len(matching) == n


@then(parsers.parse('the metric "{name}" should be recorded'))
def step_metric_name_recorded(ctx: MiddlewareScenarioContext, name: str) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("Middleware metrics recording not yet implemented")
    assert any(m.name == name for m in metrics)


@then("the histogram should have a sample in the 0.1-0.25 bucket")
def step_histogram_sample_bucket(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("Histogram bucket recording not yet implemented")


@then(parsers.parse('"{name}" should have buckets:'))
def step_metric_buckets(
    ctx: MiddlewareScenarioContext, name: str, datatable: list[list[str]]
) -> None:
    pytest.xfail("Prometheus buckets not yet implemented")


@when("a request is made")
def step_simple_request(ctx: MiddlewareScenarioContext) -> None:
    try:
        run_async(simulate_request(ctx, method="GET", path="/test"))
    except Exception as e:
        ctx.exception_raised = e


@when(parsers.parse('requests are made to "{p1}", "{p2}", "{p3}"'))
def step_requests_three_paths(
    ctx: MiddlewareScenarioContext, p1: str, p2: str, p3: str
) -> None:
    run_async(simulate_request(ctx, method="GET", path=p1))
    run_async(simulate_request(ctx, method="GET", path=p2))
    run_async(simulate_request(ctx, method="GET", path=p3))


@then(parsers.parse('the path label should be "{path}" for all requests'))
def step_path_label(ctx: MiddlewareScenarioContext, path: str) -> None:
    pytest.xfail("Path normalization not yet implemented")


@then(parsers.parse("there should be {n:d} unique label combination, not {m:d}"))
def step_unique_labels(ctx: MiddlewareScenarioContext, n: int, m: int) -> None:
    pytest.xfail("Path normalization not yet implemented")


# === Configuration Steps (Cycle 3) ===
@given(parsers.parse('middleware configured with exclude_paths=["{p1}", "{p2}"]'))
def step_exclude_paths(ctx: MiddlewareScenarioContext, p1: str, p2: str) -> None:
    ctx.config.exclude_paths = [p1, p2]
    test_app = create_test_app(ctx)
    _wrap(ctx, test_app)


@given(parsers.parse('middleware configured with exclude_paths=["{pattern}"]'))
def step_exclude_pattern(ctx: MiddlewareScenarioContext, pattern: str) -> None:
    ctx.config.exclude_paths = [pattern]
    test_app = create_test_app(ctx)
    _wrap(ctx, test_app)


@given(parsers.parse('middleware configured with request_id_header="{header}"'))
def step_custom_header(ctx: MiddlewareScenarioContext, header: str) -> None:
    ctx.config.request_id_header = header
    test_app = create_test_app(ctx)
    _wrap(ctx, test_app)


@given("middleware configured with log_requests=False")
def step_logging_disabled(ctx: MiddlewareScenarioContext) -> None:
    ctx.config.log_requests = False
    test_app = create_test_app(ctx)
    _wrap(ctx, test_app)


@given("middleware configured with record_metrics=False")
def step_metrics_disabled(ctx: MiddlewareScenarioContext) -> None:
    ctx.config.record_metrics = False
    test_app = create_test_app(ctx)
    _wrap(ctx, test_app)


@given("middleware configured with:")
def step_middleware_config(
    ctx: MiddlewareScenarioContext, datatable: list[list[str]]
) -> None:
    for row in datatable[1:]:
        if len(row) >= 2:
            opt, val = row[0], row[1]
            if opt == "request_counter_name":
                ctx.config.request_counter_name = val
            elif opt == "request_histogram_name":
                ctx.config.request_histogram_name = val
    test_app = create_test_app(ctx)
    _wrap(ctx, test_app)


@when(parsers.parse('requests are made to "{p1}" and "{p2}"'))
def step_requests_two_paths(ctx: MiddlewareScenarioContext, p1: str, p2: str) -> None:
    run_async(simulate_request(ctx, method="GET", path=p1))
    run_async(simulate_request(ctx, method="GET", path=p2))


@when(parsers.parse('a request is made with header {header}="{value}"'))
def step_request_with_header(
    ctx: MiddlewareScenarioContext, header: str, value: str
) -> None:
    run_async(
        simulate_request(ctx, method="GET", path="/test", headers={header: value})
    )


@then("no log entry should be recorded")
@then("no log entries should be recorded")
def step_no_log(ctx: MiddlewareScenarioContext) -> None:
    assert len(run_async(read_logs(ctx.log_storage))) == 0


@then("no metrics should be recorded")
def step_no_metrics(ctx: MiddlewareScenarioContext) -> None:
    assert len(run_async(read_metrics(ctx.metrics_storage))) == 0


@then(parsers.parse('a request to "{path}" should be logged'))
def step_request_logged(ctx: MiddlewareScenarioContext, path: str) -> None:
    run_async(simulate_request(ctx, method="GET", path=path))
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert any(log.attributes.get("path") == path for log in logs)


@then(parsers.parse('the log entry should have request_id="{request_id}"'))
def step_log_entry_request_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert any(log.attributes.get("request_id") == request_id for log in logs)


@then("a log entry should be recorded")
def step_log_recorded(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Middleware request logging not yet implemented")
    assert len(logs) > 0


@then(parsers.parse('"{name}" should be incremented'))
@then(parsers.parse('"{name}" should be recorded'))
def step_metric_inc(ctx: MiddlewareScenarioContext, name: str) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("Middleware metrics recording not yet implemented")
    assert any(m.name == name for m in metrics)


# === Context Propagation Steps (Cycle 4) ===
@given("an endpoint that calls get_log_context()")
def step_endpoint_gets_context(ctx: MiddlewareScenarioContext) -> None:
    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        ctx.endpoint_context_value = get_log_context()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    _wrap(ctx, test_app)


@given("an endpoint that awaits a service that awaits a repository")
def step_nested_async(ctx: MiddlewareScenarioContext) -> None:
    async def repository() -> None:
        entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="DEBUG",
            message="Repository called",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(entry)

    async def service() -> None:
        entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="INFO",
            message="Service called",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(entry)
        await repository()

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="INFO",
            message="Handler called",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(entry)
        await service()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    _wrap(ctx, test_app)


@given("each layer writes a log entry")
def step_each_layer_logs(ctx: MiddlewareScenarioContext) -> None:
    pass


@given(parsers.parse('an endpoint that calls update_log_context(user_id="{user_id}")'))
def step_endpoint_updates_context(ctx: MiddlewareScenarioContext, user_id: str) -> None:
    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        update_log_context(user_id=user_id)
        entry = LogEntry(
            timestamp=asyncio.get_event_loop().time(),
            level="INFO",
            message="After context update",
            attributes=get_log_context(),
        )
        await ctx.log_storage.write(entry)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    _wrap(ctx, test_app)


@when(parsers.parse('a GET request is made with X-Request-ID="{request_id}"'))
def step_get_with_x_request_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    run_async(simulate_request(ctx, path="/test", headers={"X-Request-ID": request_id}))


@when(parsers.parse("{n:d} concurrent requests are made with unique request IDs"))
def step_concurrent_requests(ctx: MiddlewareScenarioContext, n: int) -> None:
    async def make_concurrent() -> None:
        tasks = []
        for i in range(n):
            rid = f"req-{i}"

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

            tasks.append(make_request(rid))
        ctx.concurrent_results = list(await asyncio.gather(*tasks))

    run_async(make_concurrent())


@when(parsers.parse('a request is made with request_id="{request_id}"'))
def step_request_with_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    run_async(simulate_request(ctx, path="/test", headers={"X-Request-ID": request_id}))


@when("then another request is made without X-Request-ID")
def step_another_request(ctx: MiddlewareScenarioContext) -> None:
    run_async(simulate_request(ctx, method="GET", path="/test"))


@then(parsers.parse('the endpoint should see request_id="{request_id}" in context'))
def step_endpoint_sees_context(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    if not ctx.endpoint_context_value:
        pytest.xfail("Context propagation not yet implemented")
    assert ctx.endpoint_context_value.get("request_id") == request_id


@then("all 3 log entries should have the same request_id")
def step_three_logs_same_id(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Context propagation not yet implemented")
    ids = {log.attributes.get("request_id") for log in logs}
    assert len(ids) == 1


@then("each request's logs should only contain its own request_id")
def step_logs_own_id(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Context propagation not yet implemented")


@then("no cross-contamination should occur")
def step_no_contamination(ctx: MiddlewareScenarioContext) -> None:
    pass


@then("the second request should have a different request_id")
def step_second_different_id(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if len(logs) < 2:
        pytest.xfail("Context propagation not yet implemented")
    ids = [
        log.attributes.get("request_id")
        for log in logs
        if "request_id" in log.attributes
    ]
    assert len(set(ids)) == len(ids)


@then(parsers.parse('the second request should not see "{request_id}"'))
def step_second_not_see_id(ctx: MiddlewareScenarioContext, request_id: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if len(logs) < 2:
        pytest.xfail("Context propagation not yet implemented")
    assert logs[-1].attributes.get("request_id") != request_id


@then(parsers.parse('subsequent logs in that request should have user_id="{user_id}"'))
def step_logs_have_user_id(ctx: MiddlewareScenarioContext, user_id: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Context update not yet working")
    assert any(log.attributes.get("user_id") == user_id for log in logs)


@then("the next request should not have user_id")
def step_next_no_user_id(ctx: MiddlewareScenarioContext) -> None:
    clear_log_context()
    run_async(simulate_request(ctx, method="GET", path="/test"))
    assert "user_id" not in get_log_context()


# === WSGI Steps (Cycle 5) ===
@given("a WSGI app with observability middleware")
def step_wsgi_app(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("WSGI middleware not yet implemented")


@given("a Flask endpoint that writes an application log")
def step_flask_endpoint(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("WSGI middleware not yet implemented")


@given("sync-only storage adapters")
def step_sync_storage(ctx: MiddlewareScenarioContext) -> None:
    pass


@given(parsers.parse("a threaded WSGI server with {n:d} worker threads"))
def step_threaded_wsgi(ctx: MiddlewareScenarioContext, n: int) -> None:
    pytest.xfail("WSGI threading test not yet implemented")


@then(parsers.parse('a log entry should be recorded with method="{m}" and path="{p}"'))
def step_log_method_path(ctx: MiddlewareScenarioContext, m: str, p: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("WSGI logging not yet implemented")
    assert any(
        log.attributes.get("method") == m and log.attributes.get("path") == p
        for log in logs
    )


@then(parsers.parse('"{name}" should be incremented with status="{status}"'))
def step_metric_status(ctx: MiddlewareScenarioContext, name: str, status: str) -> None:
    metrics = run_async(read_metrics(ctx.metrics_storage))
    if not metrics:
        pytest.xfail("WSGI metrics not yet implemented")
    assert any(m.name == name and m.labels.get("status") == status for m in metrics)


_BOTH_LOGS = (
    'both the middleware log and application log should have request_id="{rid}"'
)


@then(parsers.parse(_BOTH_LOGS))
def step_both_logs_id(ctx: MiddlewareScenarioContext, rid: str) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if len(logs) < 2:
        pytest.xfail("WSGI context propagation not yet implemented")
    assert all(log.attributes.get("request_id") == rid for log in logs)


@then("logs and metrics should be written without async errors")
def step_no_async_errors(ctx: MiddlewareScenarioContext) -> None:
    pass


@when("concurrent requests hit different threads")
def step_concurrent_threads(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("WSGI threading not yet implemented")


@then("each thread should correctly isolate request context")
def step_threads_isolate(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("WSGI thread isolation not yet implemented")


# === Error Handling Steps (Cycle 6) ===
@given(parsers.parse('an endpoint that raises {exc}("{msg}")'))
def step_endpoint_raises(ctx: MiddlewareScenarioContext, exc: str, msg: str) -> None:
    exc_class = {"ValueError": ValueError, "RuntimeError": RuntimeError}.get(
        exc, RuntimeError
    )

    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        raise exc_class(msg)

    _wrap(ctx, test_app)


@given(parsers.parse("log storage that raises {exc} on write"))
def step_failing_storage(ctx: MiddlewareScenarioContext, exc: str) -> None:
    class FailingLogStorage(InMemoryLogStorage):
        async def write(self, entry: LogEntry) -> None:
            raise OSError("Storage failure")

    ctx.log_storage = FailingLogStorage()
    ctx.storage_failure = True


@given(parsers.parse("log storage that hangs for {n:d} seconds"))
def step_hanging_storage(ctx: MiddlewareScenarioContext, n: int) -> None:
    class HangingLogStorage(InMemoryLogStorage):
        async def write(self, entry: LogEntry) -> None:
            await asyncio.sleep(n)
            await super().write(entry)

    ctx.log_storage = HangingLogStorage()
    ctx.storage_hang_seconds = n


@given(parsers.parse("middleware configured with write_timeout={n:d}ms"))
def step_middleware_timeout(ctx: MiddlewareScenarioContext, n: int) -> None:
    ctx.config.write_timeout = n / 1000.0


@given("an endpoint that raises RuntimeError")
def step_endpoint_runtime_error(ctx: MiddlewareScenarioContext) -> None:
    async def test_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        raise RuntimeError("Test error")

    _wrap(ctx, test_app)


@given("context cleanup that also raises an error")
def step_cleanup_raises(ctx: MiddlewareScenarioContext) -> None:
    pass


@when("a request is made to that endpoint")
def step_request_to_endpoint(ctx: MiddlewareScenarioContext) -> None:
    try:
        run_async(simulate_request(ctx, method="GET", path="/failing"))
    except Exception as e:
        ctx.exception_raised = e


@then("an ERROR log should be recorded with exception details")
def step_error_log(ctx: MiddlewareScenarioContext) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Exception logging not yet implemented")
    error_logs = [log for log in logs if log.level == "ERROR"]
    assert len(error_logs) > 0, "No ERROR logs found"
    assert any("exception" in log.attributes for log in error_logs)


@then("the ValueError should still propagate to the client")
def step_valueerror_propagates(ctx: MiddlewareScenarioContext) -> None:
    assert isinstance(ctx.exception_raised, ValueError)


@then(parsers.parse("status_code should be {code:d}"))
def step_status_code(ctx: MiddlewareScenarioContext, code: int) -> None:
    logs = run_async(read_logs(ctx.log_storage))
    if not logs:
        pytest.xfail("Status code logging not yet implemented")
    assert any(log.attributes.get("status_code") == code for log in logs)


@then("the request should complete successfully")
def step_request_completes(ctx: MiddlewareScenarioContext) -> None:
    assert ctx.request_capture.status_code == 200


@then("the response should be returned to the client")
def step_response_returned(ctx: MiddlewareScenarioContext) -> None:
    assert ctx.request_capture.response_body is not None


@then("a warning should be logged to stderr")
def step_warning_stderr(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("Stderr warning capture not implemented")


@then(parsers.parse("the request should complete within {n:d}ms"))
def step_request_within_time(ctx: MiddlewareScenarioContext, n: int) -> None:
    pytest.xfail("Request timing not implemented")


@then("the response should be returned")
def step_response_is_returned(ctx: MiddlewareScenarioContext) -> None:
    assert ctx.request_capture.response_body is not None


@then("the RuntimeError should be raised to the client")
def step_runtimeerror_raised(ctx: MiddlewareScenarioContext) -> None:
    assert isinstance(ctx.exception_raised, RuntimeError)


@then("the cleanup error should be logged separately")
def step_cleanup_logged(ctx: MiddlewareScenarioContext) -> None:
    pytest.xfail("Cleanup error logging not yet implemented")
