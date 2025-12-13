# observabilipy

Framework-agnostic metrics and structured log collection with hexagonal architecture.

Develop observability features decoupled from your infrastructure. Use embedded storage (SQLite, in-memory) during development, then optionally expose endpoints for scraping by Prometheus, Grafana Alloy, or other observability platforms when you're ready.

## Features

- **Prometheus-style metrics** - `/metrics` endpoint in text format
- **Structured logs** - `/logs` endpoint in NDJSON (Grafana Alloy compatible)
- **Framework adapters** - FastAPI, Django, ASGI, WSGI
- **Storage backends** - In-memory, SQLite (with WAL), Ring buffer
- **Retention policies** - Automatic cleanup with EmbeddedRuntime

## Installation

```bash
git clone https://github.com/PhilHem/observabilipy.git
cd observabilipy
uv sync
```

For framework support:

```bash
uv sync --extra fastapi
uv sync --extra django
```

## Quick Start

```python
from fastapi import FastAPI
from observabilipy import InMemoryLogStorage, InMemoryMetricsStorage
from observabilipy.adapters.frameworks.fastapi import create_observability_router

app = FastAPI()
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

app.include_router(create_observability_router(log_storage, metrics_storage))
```

Run with `uvicorn` and visit:
- `/logs` - NDJSON logs (with optional `?since=<timestamp>&level=<level>`)
- `/metrics` - NDJSON metrics (with optional `?since=<timestamp>`)
- `/metrics/prometheus` - Prometheus text format (latest value per metric)

## Recording Metrics and Logs

Use the helper functions for a cleaner API:

```python
from observabilipy import info, error, counter, gauge

# Log entries with level-specific helpers
await log_storage.write(info("User logged in", user_id=123, ip="192.168.1.1"))
await log_storage.write(error("Payment failed", order_id=456, reason="timeout"))

# Metrics with semantic helpers
await metrics_storage.write(counter("http_requests_total", method="GET", path="/api/users"))
await metrics_storage.write(gauge("active_connections", value=42))
```

### Context Managers

```python
from observabilipy import timer, timed_log

# Auto-record timing to histogram
async with timer(metrics_storage, "request_duration_seconds", method="GET"):
    await handle_request()

# Log entry and exit with elapsed time
async with timed_log(log_storage, "Processing order", order_id=123):
    await process_order()
```

### Exception Logging

```python
from observabilipy import log_exception

try:
    risky_operation()
except Exception:
    await log_storage.write(log_exception("Operation failed", operation="risky"))
```

### Raw Model Access

For full control, use the models directly:

```python
import time
from observabilipy import LogEntry, MetricSample

await log_storage.write(
    LogEntry(
        timestamp=time.time(),
        level="INFO",
        message="User logged in",
        attributes={"user_id": 123},
    )
)

await metrics_storage.write(
    MetricSample(
        name="http_requests_total",
        timestamp=time.time(),
        value=1.0,
        labels={"method": "GET"},
    )
)
```

## Storage Backends

| Backend | Use Case |
|---------|----------|
| `InMemoryLogStorage` / `InMemoryMetricsStorage` | Development and testing |
| `SQLiteLogStorage` / `SQLiteMetricsStorage` | Persistent storage with WAL mode for concurrent access |
| `RingBufferLogStorage` / `RingBufferMetricsStorage` | Fixed-size buffer for memory-constrained environments |

All backends implement the same port interfaces and are interchangeable.

## Examples

See the [examples/](examples/) directory:

| Example | Description |
|---------|-------------|
| [minimal_example.py](examples/minimal_example.py) | Dummy metrics and logs generator for testing |
| [cgroups_example.py](examples/cgroups_example.py) | Container CPU and memory metrics from cgroups v2 |
| [fastapi_example.py](examples/fastapi_example.py) | Basic FastAPI setup with in-memory storage |
| [django_example.py](examples/django_example.py) | Django integration |
| [asgi_example.py](examples/asgi_example.py) | Generic ASGI middleware |
| [sqlite_example.py](examples/sqlite_example.py) | Persistent storage with SQLite |
| [ring_buffer_example.py](examples/ring_buffer_example.py) | Fixed-size storage for constrained environments |
| [embedded_runtime_example.py](examples/embedded_runtime_example.py) | Background retention cleanup |

