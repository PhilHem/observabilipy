"""Example FastAPI application with observability endpoints.

Run with:
    uvicorn examples.fastapi_example:app --reload

Endpoints:
    /metrics              - NDJSON metrics (all samples)
    /metrics?since=<ts>   - NDJSON metrics since timestamp (incremental)
    /metrics/prometheus   - Prometheus text format (latest per metric)
    /logs                 - NDJSON logs (all entries)
    /logs?since=<ts>      - NDJSON logs since timestamp
    /logs?level=<level>   - NDJSON logs filtered by level (INFO, ERROR, etc.)
"""

import time

from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

# Create storage instances
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Create FastAPI app
app = FastAPI(title="Observability Example")

# Mount observability endpoints
app.include_router(create_observability_router(log_storage, metrics_storage))


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint that logs a message and increments a counter."""
    # Log the request
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Root endpoint called",
            attributes={"path": "/"},
        )
    )

    # Record a metric
    await metrics_storage.write(
        MetricSample(
            name="http_requests_total",
            timestamp=time.time(),
            value=1.0,
            labels={"method": "GET", "path": "/"},
        )
    )

    return {"message": "Hello! Check /metrics and /logs endpoints."}
