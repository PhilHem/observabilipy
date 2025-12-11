# observabilipy

Framework-agnostic metrics and structured log collection with hexagonal architecture.

Develop observability features decoupled from your infrastructure. Use embedded storage (SQLite, in-memory) during development, then optionally expose endpoints for scraping by Prometheus, Grafana Alloy, or other observability platforms when you're ready.

## Features

- **Prometheus-style metrics** - `/metrics` endpoint in text format
- **Structured logs** - `/logs` endpoint in NDJSON (Grafana Alloy compatible)
- **Framework adapters** - FastAPI, Django, generic ASGI
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
from observability.adapters.frameworks.fastapi import create_observability_router
from observability.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)

app = FastAPI()
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

app.include_router(create_observability_router(log_storage, metrics_storage))
```

Run with `uvicorn` and visit `/metrics` and `/logs`.

## Recording Metrics and Logs

```python
import time
from observability.core.models import LogEntry, MetricSample

# Record a log entry
await log_storage.write(
    LogEntry(
        timestamp=time.time(),
        level="INFO",
        message="User logged in",
        attributes={"user_id": 123, "ip": "192.168.1.1"},
    )
)

# Record a metric sample
await metrics_storage.write(
    MetricSample(
        name="http_requests_total",
        timestamp=time.time(),
        value=1.0,
        labels={"method": "GET", "path": "/api/users"},
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

