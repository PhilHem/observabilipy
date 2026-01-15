"""Minimal example exposing dummy metrics and logs.

Run with:
    uvicorn examples.minimal_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from itertools import cycle

from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()


async def generate_dummy_data() -> None:
    """Generate dummy metrics and logs every second."""
    endpoints = ["/api/users", "/api/orders", "/api/products", "/health"]
    methods = ["GET", "POST", "PUT", "DELETE"]
    levels = ["DEBUG", "INFO", "INFO", "INFO", "WARN", "ERROR"]
    statuses = ["200", "200", "200", "404", "500"]

    # Use cycle to generate deterministic sequences
    endpoint_cycle = cycle(endpoints)
    method_cycle = cycle(methods)
    status_cycle = cycle(statuses)
    level_cycle = cycle(levels)

    # Deterministic metric values
    response_times = [0.05, 0.12, 0.08, 0.25, 0.10]
    cpu_values = [15.5, 22.3, 18.7, 35.2, 28.9]
    memory_values = [125.5, 185.3, 156.2, 245.8, 195.4]
    request_ids = [1001, 2002, 3003, 4004, 5005]

    response_time_cycle = cycle(response_times)
    cpu_cycle = cycle(cpu_values)
    memory_cycle = cycle(memory_values)
    request_id_cycle = cycle(request_ids)

    while True:
        now = time.time()

        # Record HTTP request metrics (fixed count of 3 per iteration)
        for _ in range(3):
            await metrics_storage.write(
                MetricSample(
                    name="http_requests_total",
                    timestamp=now,
                    value=1.0,
                    labels={
                        "method": next(method_cycle),
                        "path": next(endpoint_cycle),
                        "status": next(status_cycle),
                    },
                )
            )

        # Record response time metrics
        await metrics_storage.write(
            MetricSample(
                name="http_request_duration_seconds",
                timestamp=now,
                value=next(response_time_cycle),
                labels={"path": next(endpoint_cycle)},
            )
        )

        # Record system metrics
        await metrics_storage.write(
            MetricSample(
                name="process_cpu_percent",
                timestamp=now,
                value=next(cpu_cycle),
                labels={},
            )
        )
        await metrics_storage.write(
            MetricSample(
                name="process_memory_mb",
                timestamp=now,
                value=next(memory_cycle),
                labels={},
            )
        )

        # Record a log entry
        level = next(level_cycle)
        messages = {
            "DEBUG": "Cache lookup for key user:123",
            "INFO": "Request processed successfully",
            "WARN": "Slow query detected (>100ms)",
            "ERROR": "Failed to connect to database",
        }
        await log_storage.write(
            LogEntry(
                timestamp=now,
                level=level,
                message=messages[level],
                attributes={
                    "request_id": f"req-{next(request_id_cycle)}",
                    "service": "api",
                },
            )
        )

        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Start background data generation on startup."""
    task = asyncio.create_task(generate_dummy_data())
    yield
    task.cancel()


app = FastAPI(title="Minimal Observability Example", lifespan=lifespan)
app.include_router(create_observability_router(log_storage, metrics_storage))
