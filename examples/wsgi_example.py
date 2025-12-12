"""Example standalone WSGI application with observability endpoints.

This example demonstrates using the WSGI adapter without Flask or other frameworks.
It works with any WSGI server (gunicorn, uWSGI, waitress).

Run with:
    python examples/wsgi_example.py
    # or with gunicorn
    gunicorn examples.wsgi_example:app

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/logs?since=0 - Logs since timestamp
"""

import asyncio
import time

from observabilipy.adapters.frameworks.wsgi import create_wsgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

# Create storage instances
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Create the WSGI app with observability endpoints
app = create_wsgi_app(log_storage, metrics_storage)


async def _demo_data() -> None:
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


def demo_data() -> None:
    """Synchronous wrapper to add demo data."""
    asyncio.run(_demo_data())


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    # Add demo data before starting
    demo_data()
    print("Starting WSGI server on http://localhost:8000")
    print("Visit http://localhost:8000/metrics or http://localhost:8000/logs")
    server = make_server("0.0.0.0", 8000, app)
    server.serve_forever()
