"""Metric helper functions for creating MetricSample objects."""

import time
from collections.abc import Generator
from contextlib import contextmanager

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

    Example:
        >>> sample = counter("http_requests_total", labels={"method": "GET"})
        >>> sample.name
        'http_requests_total'
        >>> sample.value
        1.0
        >>> sample.labels
        {'method': 'GET'}
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

    Example:
        >>> sample = gauge("cpu_percent", 45.2, labels={"host": "server1"})
        >>> sample.name
        'cpu_percent'
        >>> sample.value
        45.2
    """
    return MetricSample(
        name=name,
        timestamp=time.time(),
        value=value,
        labels=labels or {},
    )


DEFAULT_HISTOGRAM_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]


def histogram(
    name: str,
    value: float,
    labels: dict[str, str] | None = None,
    buckets: list[float] | None = None,
) -> list[MetricSample]:
    """Create histogram metric samples for a single observation.

    Args:
        name: Metric name (e.g., "http_request_duration_seconds")
        value: Observed value
        labels: Optional dimension labels
        buckets: Bucket boundaries (default: Prometheus standard buckets)

    Returns:
        List of MetricSample objects (bucket samples + sum + count)

    Example:
        >>> samples = histogram("request_duration", 0.25, buckets=[0.1, 0.5, 1.0])
        >>> len(samples)
        6
        >>> samples[-2].name, samples[-1].name
        ('request_duration_sum', 'request_duration_count')
    """
    timestamp = time.time()
    base_labels = labels or {}
    bucket_boundaries = buckets if buckets is not None else DEFAULT_HISTOGRAM_BUCKETS

    samples: list[MetricSample] = []

    # Create bucket samples with cumulative counts
    for boundary in bucket_boundaries:
        bucket_labels = {**base_labels, "le": str(boundary)}
        bucket_value = 1.0 if value <= boundary else 0.0
        samples.append(
            MetricSample(
                name=f"{name}_bucket",
                timestamp=timestamp,
                value=bucket_value,
                labels=bucket_labels,
            )
        )

    # Always add +Inf bucket (always contains the observation)
    inf_labels = {**base_labels, "le": "+Inf"}
    samples.append(
        MetricSample(
            name=f"{name}_bucket",
            timestamp=timestamp,
            value=1.0,
            labels=inf_labels,
        )
    )

    # Add sum sample
    samples.append(
        MetricSample(
            name=f"{name}_sum",
            timestamp=timestamp,
            value=value,
            labels=base_labels,
        )
    )

    # Add count sample
    samples.append(
        MetricSample(
            name=f"{name}_count",
            timestamp=timestamp,
            value=1.0,
            labels=base_labels,
        )
    )

    return samples


class TimerResult:
    """Result object for timer context manager."""

    def __init__(self) -> None:
        self.samples: list[MetricSample] = []


@contextmanager
def timer(
    name: str,
    labels: dict[str, str] | None = None,
    buckets: list[float] | None = None,
) -> Generator[TimerResult]:
    """Context manager that measures elapsed time and records as histogram.

    Args:
        name: Metric name (e.g., "http_request_duration_seconds")
        labels: Optional dimension labels
        buckets: Bucket boundaries (default: Prometheus standard buckets)

    Yields:
        TimerResult with samples populated after context exits

    Example:
        >>> with timer("request_duration", labels={"method": "GET"}) as t:
        ...     pass  # do work here
        >>> len(t.samples) > 0
        True
        >>> any(s.name == "request_duration_sum" for s in t.samples)
        True
    """
    result = TimerResult()
    start = time.perf_counter()
    yield result
    elapsed = time.perf_counter() - start
    result.samples = histogram(name, elapsed, labels=labels, buckets=buckets)
