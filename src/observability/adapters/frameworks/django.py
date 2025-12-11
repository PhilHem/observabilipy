"""Django adapter for observability endpoints.

Note: This adapter uses async views and requires ASGI (e.g., uvicorn, daphne).
For WSGI deployments, use the core components directly with async_to_sync wrappers.
"""

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, path

from observability.core.encoding.ndjson import encode_logs
from observability.core.encoding.prometheus import encode_metrics
from observability.core.ports import LogStoragePort, MetricsStoragePort


def create_observability_urlpatterns(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
) -> list[URLPattern]:
    """Create Django URL patterns with /metrics and /logs endpoints.

    Args:
        log_storage: Storage adapter implementing LogStoragePort.
        metrics_storage: Storage adapter implementing MetricsStoragePort.

    Returns:
        List of URLPattern with /metrics and /logs endpoints configured.
    """

    async def get_metrics(request: HttpRequest) -> HttpResponse:
        """Return metrics in Prometheus text format."""
        body = await encode_metrics(metrics_storage.scrape())
        return HttpResponse(
            content=body,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )

    async def get_logs(request: HttpRequest) -> HttpResponse:
        """Return logs in NDJSON format.

        Query parameters:
            since: Unix timestamp. Returns entries with timestamp > since.
        """
        since = float(request.GET.get("since", 0))
        body = await encode_logs(log_storage.read(since=since))
        return HttpResponse(
            content=body,
            content_type="application/x-ndjson",
        )

    return [
        path("metrics", get_metrics, name="observability_metrics"),
        path("logs", get_logs, name="observability_logs"),
    ]
