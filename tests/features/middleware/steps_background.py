"""Background step definitions for middleware BDD tests."""

from pytest_bdd import given
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    InMemoryLogStorage,
    InMemoryMetricsStorage,
    MiddlewareScenarioContext,
    create_test_app,
)


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
    test_app = create_test_app(ctx)
    ctx.app = ASGIObservabilityMiddleware(
        app=test_app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
    )
