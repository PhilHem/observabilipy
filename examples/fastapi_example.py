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

Instrumentation:
    This example demonstrates automatic metrics collection using the
    `Instrumented` context manager via FastAPI dependency injection.
"""

import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI

from observabilipy.adapters.frameworks.fastapi import (
    Instrumented,
    create_instrumented_dependency,
    create_observability_router,
)
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)

# Create storage instances
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Create FastAPI app
app = FastAPI(title="Observability Example")

# Mount observability endpoints
app.include_router(create_observability_router(log_storage, metrics_storage))

# Create instrumentation dependency
get_instrumented = create_instrumented_dependency(metrics_storage)


@app.get("/")
async def root(
    instr: Annotated[Instrumented, Depends(get_instrumented)],
) -> dict[str, str]:
    """Root endpoint with automatic metrics instrumentation.

    Uses the Instrumented context manager to automatically record:
    - root_total counter (incremented on each request, with status label)
    - root_duration_seconds histogram (request timing)
    """
    async with instr("root", labels={"path": "/"}):
        # Simulate some work
        await asyncio.sleep(0.01)
        return {"message": "Hello! Check /metrics and /logs endpoints."}


@app.get("/users")
async def get_users(
    instr: Annotated[Instrumented, Depends(get_instrumented)],
) -> dict[str, list[dict[str, str]]]:
    """Users endpoint demonstrating instrumentation with custom labels.

    Records metrics with 'endpoint' label to distinguish from other routes.
    """
    async with instr("api_request", labels={"endpoint": "users", "method": "GET"}):
        # Simulate database fetch
        await asyncio.sleep(0.05)
        return {
            "users": [
                {"id": "1", "name": "Alice"},
                {"id": "2", "name": "Bob"},
            ]
        }


@app.get("/error")
async def error_endpoint(
    instr: Annotated[Instrumented, Depends(get_instrumented)],
) -> dict[str, str]:
    """Error endpoint demonstrating error status in metrics.

    When an exception occurs inside the instrumented block, the counter
    records status=error instead of status=success.
    """
    async with instr("error_demo"):
        raise ValueError("Intentional error for demonstration")
