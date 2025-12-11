"""Example FastAPI app with persistent SQLite storage.

This example demonstrates SQLite storage for logs and metrics that persist
across application restarts. Data is stored in .db files in the working directory.

Run with:
    uv run uvicorn examples.sqlite_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/ - Demo endpoint that logs requests
"""

import time

from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.sqlite import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.core.models import LogEntry, MetricSample

# SQLite storage (persists to files in working directory)
log_storage = SQLiteLogStorage("logs.db")
metrics_storage = SQLiteMetricsStorage("metrics.db")

app = FastAPI(title="SQLite Storage Example")
app.include_router(create_observability_router(log_storage, metrics_storage))


@app.get("/")
async def root() -> dict[str, str]:
    """Demo endpoint that logs a message and records a metric."""
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Root endpoint called",
            attributes={"path": "/"},
        )
    )
    await metrics_storage.write(
        MetricSample(
            name="http_requests_total",
            timestamp=time.time(),
            value=1.0,
            labels={"method": "GET", "path": "/"},
        )
    )
    return {"message": "Hello! Check /metrics and /logs endpoints."}
