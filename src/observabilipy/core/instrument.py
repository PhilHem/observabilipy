"""Instrumentation decorator for automatic metrics collection."""

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from observabilipy.core.metrics import counter, histogram
from observabilipy.core.models import MetricSample

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class InstrumentResult:
    """Result from an instrumented function call.

    Attributes:
        value: The return value from the wrapped function.
        samples: List of MetricSample objects generated during execution.
        error: The exception raised by the wrapped function, if any.

    Example:
        >>> result = InstrumentResult(value="ok", samples=[], error=None)
        >>> result.value
        'ok'
        >>> result.error is None
        True
    """

    value: Any
    samples: list[MetricSample] = field(default_factory=list)
    error: BaseException | None = None


def _build_samples(
    name: str,
    base_labels: dict[str, str],
    status: str,
    elapsed: float,
    buckets: list[float] | None,
) -> list[MetricSample]:
    """Build counter and histogram samples."""
    samples: list[MetricSample] = []

    # Generate counter sample
    counter_labels = {**base_labels, "status": status}
    samples.append(counter(f"{name}_total", labels=counter_labels))

    # Generate histogram samples for duration
    histogram_samples = histogram(
        f"{name}_duration_seconds",
        elapsed,
        labels=base_labels,
        buckets=buckets,
    )
    samples.extend(histogram_samples)

    return samples


def instrument(
    name: str,
    labels: dict[str, str] | None = None,
    buckets: list[float] | None = None,
) -> Callable[
    [Callable[P, R]],
    Callable[P, InstrumentResult | Coroutine[Any, Any, InstrumentResult]],
]:
    """Decorator that wraps a function with counter and timer metrics.

    Args:
        name: Base metric name (produces {name}_total and {name}_duration_seconds).
        labels: Optional static labels to attach to all samples.
        buckets: Histogram bucket boundaries (default: Prometheus standard buckets).

    Returns:
        Wrapped function that returns InstrumentResult containing the
        original return value and generated MetricSample objects.

    Works with both sync and async functions. For async functions, the wrapper
    is also async and must be awaited.

    Example:
        >>> @instrument("process_order", labels={"service": "orders"})
        ... def process(order_id: int) -> str:
        ...     return f"processed-{order_id}"
        >>> result = process(123)
        >>> result.value
        'processed-123'
        >>> any(s.name == "process_order_total" for s in result.samples)
        True
    """
    base_labels = labels or {}

    def decorator(
        func: Callable[P, R],
    ) -> Callable[P, InstrumentResult | Coroutine[Any, Any, InstrumentResult]]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(
                *args: P.args, **kwargs: P.kwargs
            ) -> InstrumentResult:
                value: Any = None
                error: BaseException | None = None
                status = "success"

                start = time.perf_counter()
                try:
                    value = await func(*args, **kwargs)
                except BaseException as e:
                    error = e
                    status = "error"
                elapsed = time.perf_counter() - start

                samples = _build_samples(name, base_labels, status, elapsed, buckets)
                return InstrumentResult(value=value, samples=samples, error=error)

            return cast(
                Callable[P, Coroutine[Any, Any, InstrumentResult]], async_wrapper
            )
        else:

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> InstrumentResult:
                value: Any = None
                error: BaseException | None = None
                status = "success"

                start = time.perf_counter()
                try:
                    value = func(*args, **kwargs)
                except BaseException as e:
                    error = e
                    status = "error"
                elapsed = time.perf_counter() - start

                samples = _build_samples(name, base_labels, status, elapsed, buckets)
                return InstrumentResult(value=value, samples=samples, error=error)

            return cast(Callable[P, InstrumentResult], sync_wrapper)

    return decorator
