"""FastAPI adapter for observability endpoints."""

import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, Query, Response

from observabilipy.core.encoding.ndjson import encode_logs, encode_ndjson
from observabilipy.core.encoding.prometheus import encode_current
from observabilipy.core.metrics import counter, histogram
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


def create_observability_router(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
) -> APIRouter:
    """Create a FastAPI router with /metrics, /metrics/prometheus, and /logs endpoints.

    Args:
        log_storage: Storage adapter implementing LogStoragePort.
        metrics_storage: Storage adapter implementing MetricsStoragePort.

    Returns:
        APIRouter with /metrics, /metrics/prometheus, and /logs endpoints configured.
    """
    router = APIRouter()

    @router.get("/metrics")
    async def get_metrics(
        since: float = Query(default=0),
    ) -> Response:
        """Return metrics in NDJSON format.

        Args:
            since: Unix timestamp. Returns samples with timestamp > since.
        """
        body = await encode_ndjson(metrics_storage.read(since=since))
        return Response(
            content=body,
            media_type="application/x-ndjson",
        )

    @router.get("/metrics/prometheus")
    async def get_metrics_prometheus() -> Response:
        """Return metrics in Prometheus text format (latest value per metric)."""
        body = await encode_current(metrics_storage.read())
        return Response(
            content=body,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @router.get("/logs")
    async def get_logs(
        since: float = Query(default=0),
        level: str | None = Query(default=None),
    ) -> Response:
        """Return logs in NDJSON format.

        Args:
            since: Unix timestamp. Returns entries with timestamp > since.
            level: Optional log level filter (case-insensitive).
        """
        body = await encode_logs(log_storage.read(since=since, level=level))
        return Response(
            content=body,
            media_type="application/x-ndjson",
        )

    return router


class Instrumented:
    """Context manager factory for instrumenting FastAPI request operations.

    This class provides an async context manager that records counter and
    histogram metrics for operations within a request.
    """

    def __init__(self, metrics_storage: MetricsStoragePort) -> None:
        self._storage = metrics_storage

    @asynccontextmanager
    async def __call__(
        self,
        name: str,
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> AsyncGenerator[None]:
        """Create an instrumented context for an operation.

        Args:
            name: Base metric name (produces {name}_total and {name}_duration_seconds).
            labels: Optional static labels to attach to all samples.
            buckets: Histogram bucket boundaries (default: Prometheus standard buckets).

        Yields:
            None. Metrics are recorded when the context exits.
        """
        base_labels = labels or {}
        status = "success"
        start = time.perf_counter()

        try:
            yield
        except BaseException:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start

            # Write counter sample
            counter_labels = {**base_labels, "status": status}
            await self._storage.write(counter(f"{name}_total", labels=counter_labels))

            # Write histogram samples
            for sample in histogram(
                f"{name}_duration_seconds",
                elapsed,
                labels=base_labels,
                buckets=buckets,
            ):
                await self._storage.write(sample)


def create_instrumented_dependency(
    metrics_storage: MetricsStoragePort,
) -> Callable[[], Instrumented]:
    """Create a FastAPI dependency that provides instrumentation.

    Args:
        metrics_storage: Storage adapter for writing metric samples.

    Returns:
        A callable that returns an Instrumented instance for use as a
        FastAPI dependency.

    Example:
        ```python
        metrics_storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(metrics_storage)

        @app.get("/users")
        async def get_users(
            instr: Annotated[Instrumented, Depends(get_instrumented)]
        ):
            async with instr("fetch_users", labels={"source": "db"}):
                return await fetch_users()
        ```
    """

    def get_instrumented() -> Instrumented:
        return Instrumented(metrics_storage)

    return get_instrumented
