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

from fastapi import FastAPI

from examples.demo_helpers import record_demo_request
from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage import SQLiteLogStorage, SQLiteMetricsStorage

# SQLite storage (persists to files in working directory)
log_storage = SQLiteLogStorage("logs.db")
metrics_storage = SQLiteMetricsStorage("metrics.db")

app = FastAPI(title="SQLite Storage Example")
app.include_router(create_observability_router(log_storage, metrics_storage))


@app.get("/")
async def root() -> dict[str, str]:
    """Demo endpoint that logs a message and records a metric."""
    return await record_demo_request(log_storage, metrics_storage)
