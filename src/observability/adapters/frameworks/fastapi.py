"""FastAPI adapter for observability endpoints."""

from fastapi import APIRouter, Query, Response

from observability.core.encoding.ndjson import encode_logs
from observability.core.encoding.prometheus import encode_metrics
from observability.core.ports import LogStoragePort, MetricsStoragePort


def create_observability_router(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
) -> APIRouter:
    """Create a FastAPI router with /metrics and /logs endpoints.

    Args:
        log_storage: Storage adapter implementing LogStoragePort.
        metrics_storage: Storage adapter implementing MetricsStoragePort.

    Returns:
        APIRouter with /metrics and /logs endpoints configured.
    """
    router = APIRouter()

    @router.get("/metrics")
    async def get_metrics() -> Response:
        """Return metrics in Prometheus text format."""
        body = await encode_metrics(metrics_storage.scrape())
        return Response(
            content=body,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @router.get("/logs")
    async def get_logs(since: float = Query(default=0)) -> Response:
        """Return logs in NDJSON format.

        Args:
            since: Unix timestamp. Returns entries with timestamp > since.
        """
        body = await encode_logs(log_storage.read(since=since))
        return Response(
            content=body,
            media_type="application/x-ndjson",
        )

    return router
