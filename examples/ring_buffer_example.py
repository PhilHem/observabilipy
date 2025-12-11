"""Example FastAPI app with ring buffer storage for constrained environments.

This example demonstrates fixed-size in-memory storage using ring buffers.
When the buffer is full, oldest entries are automatically evicted. Useful for:
- Embedded systems with limited memory
- Services where you only need recent data
- Predictable memory usage without retention policies

Run with:
    uv run uvicorn examples.ring_buffer_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/ - Demo endpoint that logs requests
"""

import time

from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.ring_buffer import (
    RingBufferLogStorage,
    RingBufferMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

# Ring buffer storage (fixed size, oldest entries evicted when full)
log_storage = RingBufferLogStorage(max_size=1000)
metrics_storage = RingBufferMetricsStorage(max_size=1000)

app = FastAPI(title="Ring Buffer Storage Example")
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
