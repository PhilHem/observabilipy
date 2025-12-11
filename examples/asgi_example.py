"""Example standalone ASGI application with observability endpoints.

This example demonstrates using the ASGI adapter without FastAPI or Django.
It works with any ASGI server (uvicorn, hypercorn, daphne).

Run with:
    uvicorn examples.asgi_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/logs?since=0 - Logs since timestamp
"""

import time

from observabilipy.adapters.frameworks.asgi import create_asgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

# Create storage instances
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Create the ASGI app with observability endpoints
app = create_asgi_app(log_storage, metrics_storage)


async def demo_data() -> None:
    """Add some demo data to storage for testing."""
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Application started",
            attributes={"version": "1.0.0"},
        )
    )
    await metrics_storage.write(
        MetricSample(
            name="app_info",
            timestamp=time.time(),
            value=1.0,
            labels={"version": "1.0.0"},
        )
    )


if __name__ == "__main__":
    import asyncio

    import uvicorn

    # Add demo data before starting
    asyncio.run(demo_data())
    uvicorn.run(app, host="0.0.0.0", port=8000)
