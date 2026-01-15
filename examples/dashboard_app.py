"""FastAPI dashboard application setup.

Configures the FastAPI app with observability router, lifespan events,
and API endpoints for the dashboard.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.core.models import RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime

from .dashboard_html import DASHBOARD_HTML
from .dashboard_metrics_collector import collect_system_metrics

if TYPE_CHECKING:
    from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


def create_dashboard_app(
    log_storage: "LogStoragePort",
    metrics_storage: "MetricsStoragePort",
) -> FastAPI:
    """Create and configure the dashboard FastAPI application.

    Args:
        log_storage: Storage adapter for logs
        metrics_storage: Storage adapter for metrics

    Returns:
        Configured FastAPI application instance
    """
    # Retention: keep 10 minutes of data, max 1000 samples
    log_retention = RetentionPolicy(max_age_seconds=600, max_count=1000)
    metrics_retention = RetentionPolicy(max_age_seconds=600, max_count=5000)

    # Runtime handles background cleanup
    runtime = EmbeddedRuntime(
        log_storage=log_storage,
        log_retention=log_retention,
        metrics_storage=metrics_storage,
        metrics_retention=metrics_retention,
        cleanup_interval_seconds=30,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        """Start runtime and metrics collection on startup."""
        await runtime.start()
        task = asyncio.create_task(collect_system_metrics(metrics_storage))
        yield
        task.cancel()
        await runtime.stop()

    app = FastAPI(title="System Metrics Dashboard", lifespan=lifespan)
    app.include_router(create_observability_router(log_storage, metrics_storage))

    @app.get("/api/logs")
    async def get_logs_json() -> JSONResponse:
        """Return logs as JSON for the dashboard."""
        logs: list[dict] = []

        async for entry in log_storage.read():
            logs.append(
                {
                    "timestamp": entry.timestamp,
                    "level": entry.level,
                    "message": entry.message,
                    "attributes": entry.attributes,
                }
            )

        # Sort by timestamp descending (newest first)
        logs.sort(key=lambda x: x["timestamp"], reverse=True)

        # Return last 100 logs
        return JSONResponse(content=logs[:100])

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        """Serve the dashboard HTML."""
        return HTMLResponse(content=DASHBOARD_HTML)

    return app
