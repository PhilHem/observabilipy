"""System metrics dashboard with Chart.js visualization.

Captures real system CPU and memory metrics using psutil and displays them
in an interactive HTML dashboard with live-updating charts.

The dashboard uses the /metrics?since= endpoint with NDJSON format for
efficient incremental updates - only fetching new data since the last poll.

Requirements:
    pip install psutil
    # or: uv add psutil

Run with:
    uvicorn examples.dashboard_example:app --reload

Then visit:
    http://localhost:8000/ - Interactive dashboard with live charts
    http://localhost:8000/metrics - NDJSON metrics (with ?since= support)
    http://localhost:8000/metrics/prometheus - Prometheus text format
    http://localhost:8000/logs - NDJSON logs
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from examples.dashboard_html import DASHBOARD_HTML
from examples.dashboard_metrics_collector import collect_system_metrics
from observabilipy import get_logger
from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime

# Storage (in-memory for this example, use SQLite for persistence)
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Application logger
logger = get_logger("dashboard")

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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Manage application startup and shutdown."""
    # Start metrics collection
    metrics_task = asyncio.create_task(collect_system_metrics(metrics_storage))
    # Start cleanup task
    cleanup_task = asyncio.create_task(runtime.cleanup_loop())

    await logger.with_fields(event="startup").info(
        "Dashboard started - collecting system metrics"
    )

    yield

    # Cleanup on shutdown
    metrics_task.cancel()
    cleanup_task.cancel()
    try:
        await asyncio.gather(metrics_task, cleanup_task)
    except asyncio.CancelledError:
        pass


app = FastAPI(title="System Metrics Dashboard", lifespan=lifespan)

# Include observability routes
app.include_router(create_observability_router(log_storage, metrics_storage))


@app.get("/api/logs", response_class=JSONResponse)
async def api_logs() -> JSONResponse:
    """API endpoint for dashboard log fetching."""
    return await get_logs_json()


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Serve the dashboard HTML."""
    return HTMLResponse(content=DASHBOARD_HTML)
