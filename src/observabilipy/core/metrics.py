"""Metric helper functions for creating MetricSample objects."""

import time

from observabilipy.core.models import MetricSample


def counter(
    name: str,
    value: float = 1.0,
    labels: dict[str, str] | None = None,
) -> MetricSample:
    """Create a counter metric sample.

    Args:
        name: Metric name (e.g., "http_requests_total")
        value: Increment value (default: 1.0)
        labels: Optional dimension labels

    Returns:
        MetricSample with current timestamp
    """
    return MetricSample(
        name=name,
        timestamp=time.time(),
        value=value,
        labels=labels or {},
    )


def gauge(
    name: str,
    value: float,
    labels: dict[str, str] | None = None,
) -> MetricSample:
    """Create a gauge metric sample.

    Args:
        name: Metric name (e.g., "cpu_percent")
        value: Current gauge value
        labels: Optional dimension labels

    Returns:
        MetricSample with current timestamp
    """
    return MetricSample(
        name=name,
        timestamp=time.time(),
        value=value,
        labels=labels or {},
    )
