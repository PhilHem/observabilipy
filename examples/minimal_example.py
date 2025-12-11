"""Minimal example exposing dummy metrics and logs.

Run with:
    uvicorn examples.minimal_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
"""

import asyncio
import random
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
    levels = ["DEBUG", "INFO", "INFO", "INFO", "WARN", "ERROR"]  # weighted towards INFO

    while True:
        now = time.time()

        # Record HTTP request metrics
        for _ in range(random.randint(1, 5)):
            await metrics_storage.write(
                MetricSample(
                    name="http_requests_total",
                    timestamp=now,
                    value=1.0,
                    labels={
                        "method": random.choice(methods),
                        "path": random.choice(endpoints),
                        "status": random.choice(["200", "200", "200", "404", "500"]),
                    },
                )
            )

        # Record response time metrics
        await metrics_storage.write(
            MetricSample(
                name="http_request_duration_seconds",
                timestamp=now,
                value=random.uniform(0.01, 0.5),
                labels={"path": random.choice(endpoints)},
            )
        )

        # Record system metrics
        await metrics_storage.write(
            MetricSample(
                name="process_cpu_percent",
                timestamp=now,
                value=random.uniform(5, 80),
                labels={},
            )
        )
        await metrics_storage.write(
            MetricSample(
                name="process_memory_mb",
                timestamp=now,
                value=random.uniform(100, 500),
                labels={},
            )
        )

        # Record a log entry
        level = random.choice(levels)
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
                    "request_id": f"req-{random.randint(1000, 9999)}",
                    "service": "api",
                },
            )
        )

        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Start background data generation on startup."""
    asyncio.create_task(generate_dummy_data())
    yield


app = FastAPI(title="Minimal Observability Example", lifespan=lifespan)
app.include_router(create_observability_router(log_storage, metrics_storage))
