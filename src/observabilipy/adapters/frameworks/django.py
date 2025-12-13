"""Django adapter for observability endpoints.

Note: This adapter uses async views and requires ASGI (e.g., uvicorn, daphne).
For WSGI deployments, use the core components directly with async_to_sync wrappers.
"""

import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, path

from observabilipy.core.encoding.ndjson import encode_logs, encode_ndjson
from observabilipy.core.encoding.prometheus import encode_current
from observabilipy.core.metrics import counter, histogram
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

ViewFunc = TypeVar("ViewFunc", bound=Callable[..., Coroutine[Any, Any, HttpResponse]])


def create_observability_urlpatterns(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
) -> list[URLPattern]:
    """Create Django URL patterns for /metrics, /metrics/prometheus, and /logs.

    Args:
        log_storage: Storage adapter implementing LogStoragePort.
        metrics_storage: Storage adapter implementing MetricsStoragePort.

    Returns:
        List of URLPattern with /metrics, /metrics/prometheus, and /logs endpoints.
    """

    async def get_metrics(request: HttpRequest) -> HttpResponse:
        """Return metrics in NDJSON format.

        Query parameters:
            since: Unix timestamp. Returns samples with timestamp > since.
        """
        since = float(request.GET.get("since", 0))
        body = await encode_ndjson(metrics_storage.read(since=since))
        return HttpResponse(
            content=body,
            content_type="application/x-ndjson",
        )

    async def get_metrics_prometheus(request: HttpRequest) -> HttpResponse:
        """Return metrics in Prometheus text format (latest value per metric)."""
        body = await encode_current(metrics_storage.read())
        return HttpResponse(
            content=body,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )

    async def get_logs(request: HttpRequest) -> HttpResponse:
        """Return logs in NDJSON format.

        Query parameters:
            since: Unix timestamp. Returns entries with timestamp > since.
            level: Optional log level filter (case-insensitive).
        """
        since = float(request.GET.get("since", 0))
        level = request.GET.get("level")
        body = await encode_logs(log_storage.read(since=since, level=level))
        return HttpResponse(
            content=body,
            content_type="application/x-ndjson",
        )

    return [
        path("metrics", get_metrics, name="observability_metrics"),
        path(
            "metrics/prometheus",
            get_metrics_prometheus,
            name="observability_metrics_prometheus",
        ),
        path("logs", get_logs, name="observability_logs"),
    ]


def instrument_view(
    metrics_storage: MetricsStoragePort,
    name: str | None = None,
    labels: dict[str, str] | None = None,
    buckets: list[float] | None = None,
) -> Callable[[ViewFunc], ViewFunc]:
    """Decorator that instruments a Django async view with metrics.

    Records counter and histogram metrics for each request to the view.
    Automatically extracts HTTP method from the request and adds it as a label.

    Args:
        metrics_storage: Storage adapter for writing metric samples.
        name: Base metric name (defaults to view function name).
        labels: Optional static labels to attach to all samples.
        buckets: Histogram bucket boundaries (default: Prometheus standard buckets).

    Returns:
        Decorated view function that records metrics.

    Example:
        ```python
        @instrument_view(metrics_storage, name="user_api")
        async def user_list(request):
            return JsonResponse({"users": []})
        ```
    """
    base_labels = labels or {}

    def decorator(view_func: ViewFunc) -> ViewFunc:
        metric_name = name or view_func.__name__

        @wraps(view_func)
        async def wrapper(
            request: HttpRequest, *args: Any, **kwargs: Any
        ) -> HttpResponse:
            status = "success"
            start = time.perf_counter()

            try:
                response = await view_func(request, *args, **kwargs)
                return response
            except BaseException:
                status = "error"
                raise
            finally:
                elapsed = time.perf_counter() - start

                # Build labels with HTTP method
                request_labels = {
                    **base_labels,
                    "method": request.method or "UNKNOWN",
                    "status": status,
                }

                # Write counter sample
                await metrics_storage.write(
                    counter(f"{metric_name}_total", labels=request_labels)
                )

                # Write histogram samples (without status in labels)
                histogram_labels = {
                    **base_labels,
                    "method": request.method or "UNKNOWN",
                }
                for sample in histogram(
                    f"{metric_name}_duration_seconds",
                    elapsed,
                    labels=histogram_labels,
                    buckets=buckets,
                ):
                    await metrics_storage.write(sample)

        return wrapper  # type: ignore[return-value]

    return decorator
