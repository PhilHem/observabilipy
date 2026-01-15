"""Demo helpers for example applications.

This module provides common demo functionality used across multiple examples,
reducing code duplication while keeping each example self-contained and runnable.
"""

import time

from observabilipy.core.models import LogEntry, MetricSample
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


async def record_demo_request(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
    path: str = "/",
    method: str = "GET",
) -> dict[str, str]:
    """Record a demo log entry and metric for an endpoint request.

    This is a helper function used by example applications to demonstrate
    logging and metrics recording. It writes a log entry and increments
    a request counter metric.

    Args:
        log_storage: Storage backend for logs
        metrics_storage: Storage backend for metrics
        path: The request path to record
        method: The HTTP method to record

    Returns:
        A response dict with a message pointing to observability endpoints
    """
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Root endpoint called",
            attributes={"path": path},
        )
    )
    await metrics_storage.write(
        MetricSample(
            name="http_requests_total",
            timestamp=time.time(),
            value=1.0,
            labels={"method": method, "path": path},
        )
    )
    return {"message": "Hello! Check /metrics and /logs endpoints."}
