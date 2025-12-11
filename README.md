# observabilipy

Framework-agnostic metrics and structured log collection with hexagonal architecture.

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

## Examples

See the [examples/](examples/) directory:

| Example | Description |
|---------|-------------|
| [fastapi_example.py](examples/fastapi_example.py) | Basic FastAPI setup with in-memory storage |
| [django_example.py](examples/django_example.py) | Django integration |
| [asgi_example.py](examples/asgi_example.py) | Generic ASGI middleware |
| [sqlite_example.py](examples/sqlite_example.py) | Persistent storage with SQLite |
| [ring_buffer_example.py](examples/ring_buffer_example.py) | Fixed-size storage for constrained environments |
| [embedded_runtime_example.py](examples/embedded_runtime_example.py) | Background retention cleanup |

## Architecture

This library follows hexagonal architecture with pure core domain, port interfaces, and swappable adapters. See [CLAUDE.md](CLAUDE.md) for full architectural documentation.

## Development

```bash
uv sync                      # Install dependencies
uv run pytest                # Run tests
uv run mypy src/             # Type checking
uv run ruff check src/       # Linting
uv run ruff format src/      # Formatting
```
