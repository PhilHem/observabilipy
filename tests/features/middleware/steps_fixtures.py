"""Pytest fixtures for middleware BDD tests."""

from typing import Any

import pytest
from tests.features.middleware.steps_helpers import (
    ASGIObservabilityMiddleware,
    MiddlewareScenarioContext,
)

from observabilipy.adapters.logging_context import clear_log_context


@pytest.fixture
def ctx() -> MiddlewareScenarioContext:
    """Fresh scenario context for each test."""
    clear_log_context()
    return MiddlewareScenarioContext()


def wrap_app(ctx: MiddlewareScenarioContext, app: Any) -> None:
    """Wrap app with observability middleware and store in context."""
    ctx.app = ASGIObservabilityMiddleware(
        app=app,
        log_storage=ctx.log_storage,
        metrics_storage=ctx.metrics_storage,
        exclude_paths=ctx.config.exclude_paths if ctx.config.exclude_paths else None,
        request_id_header=ctx.config.request_id_header,
    )
    if hasattr(ctx.config, "log_requests"):
        ctx.app.set_log_requests(ctx.config.log_requests)
    if hasattr(ctx.config, "record_metrics"):
        ctx.app.set_record_metrics(ctx.config.record_metrics)
    if hasattr(ctx.config, "request_counter_name"):
        ctx.app.set_request_counter_name(ctx.config.request_counter_name)
    if hasattr(ctx.config, "request_histogram_name"):
        ctx.app.set_request_histogram_name(ctx.config.request_histogram_name)
