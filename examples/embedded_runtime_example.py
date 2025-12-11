"""Example FastAPI app with EmbeddedRuntime, SQLite storage, and retention policies.

This example demonstrates embedded mode with:
- SQLite for persistent log and metrics storage
- Automatic retention cleanup (deletes data older than 1 hour)
- Background cleanup task running every 60 seconds

Run with:
    uvicorn examples.embedded_runtime_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/ - Demo endpoint that logs requests
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.sqlite import SQLiteLogStorage, SQLiteMetricsStorage
from observabilipy.core.models import LogEntry, MetricSample, RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime

# SQLite storage (persists to files in working directory)
log_storage = SQLiteLogStorage("logs.db")
metrics_storage = SQLiteMetricsStorage("metrics.db")

# Retention policies: keep data for 1 hour
log_retention = RetentionPolicy(max_age_seconds=3600)
metrics_retention = RetentionPolicy(max_age_seconds=3600)

# EmbeddedRuntime handles background cleanup
runtime = EmbeddedRuntime(
    log_storage=log_storage,
    log_retention=log_retention,
    metrics_storage=metrics_storage,
    metrics_retention=metrics_retention,
    cleanup_interval_seconds=60,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Start runtime on startup, stop on shutdown."""
    await runtime.start()
    yield
    await runtime.stop()


app = FastAPI(title="Embedded Runtime Example", lifespan=lifespan)
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
