"""Django adapter for observability endpoints.

Note: This adapter uses async views and requires ASGI (e.g., uvicorn, daphne).
For WSGI deployments, use the core components directly with async_to_sync wrappers.
"""

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, path

from observabilipy.core.encoding.ndjson import encode_logs, encode_ndjson
from observabilipy.core.encoding.prometheus import encode_current
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


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
