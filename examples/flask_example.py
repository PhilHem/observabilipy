"""Example Flask application with observability endpoints.

This example demonstrates integrating observabilipy with Flask by mounting
the WSGI adapter at a sub-path.

Install Flask first:
    pip install flask

Run with:
    python examples/flask_example.py
    # or with gunicorn
    gunicorn examples.flask_example:app

Then visit:
    http://localhost:5000/ - Flask app root
    http://localhost:5000/observability/metrics - Prometheus metrics
    http://localhost:5000/observability/logs - NDJSON logs
    http://localhost:5000/observability/logs?level=INFO - Filtered logs
"""

import asyncio
import time
from collections.abc import Iterable
from typing import Any

from observabilipy.adapters.frameworks.wsgi import create_wsgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

from flask import Flask

# Create storage instances (shared across the app)
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()


def _run_async(coro: Any) -> Any:
    """Run async coroutine from sync context."""
    return asyncio.run(coro)


# Create Flask app
app = Flask(__name__)


@app.route("/")
def index() -> str:
    """Root endpoint demonstrating logging."""
    _run_async(
        log_storage.write(
            LogEntry(
                timestamp=time.time(),
                level="INFO",
                message="Root endpoint accessed",
                attributes={"path": "/"},
            )
        )
    )
    _run_async(
        metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=time.time(),
                value=1.0,
                labels={"path": "/", "method": "GET"},
            )
        )
    )
    return "Hello from Flask! Check /observability/metrics and /observability/logs"


@app.route("/api/users")
def users() -> dict[str, list[str]]:
    """Example API endpoint."""
    _run_async(
        log_storage.write(
            LogEntry(
                timestamp=time.time(),
                level="DEBUG",
                message="Users endpoint accessed",
                attributes={"path": "/api/users"},
            )
        )
    )
    return {"users": ["alice", "bob", "charlie"]}


# Create observability WSGI app
observability_app = create_wsgi_app(log_storage, metrics_storage)

# Store the original Flask WSGI app before wrapping
_original_wsgi_app = app.wsgi_app


def _dispatcher(
    environ: dict[str, Any], start_response: Any
) -> Iterable[bytes]:
    """Dispatch requests to observability app or Flask based on path."""
    path = environ.get("PATH_INFO", "")
    if path.startswith("/observability"):
        # Strip the prefix and dispatch to observability app
        environ["PATH_INFO"] = path[len("/observability"):] or "/"
        environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + "/observability"
        return observability_app(environ, start_response)
    # Fall through to Flask
    return _original_wsgi_app(environ, start_response)


# Mount observability endpoints at /observability
app.wsgi_app = _dispatcher  # type: ignore[method-assign]


if __name__ == "__main__":
    # Add startup log entry
    _run_async(
        log_storage.write(
            LogEntry(
                timestamp=time.time(),
                level="INFO",
                message="Flask application started",
                attributes={"version": "1.0.0"},
            )
        )
    )

    print("Starting Flask server on http://localhost:5000")
    print("Endpoints:")
    print("  http://localhost:5000/ - Flask root")
    print("  http://localhost:5000/api/users - Example API")
    print("  http://localhost:5000/observability/metrics - Prometheus metrics")
    print("  http://localhost:5000/observability/logs - NDJSON logs")
    app.run(host="0.0.0.0", port=5000, debug=True)
