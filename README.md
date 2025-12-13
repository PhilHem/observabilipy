# observabilipy

**Start with observability built in.**

Build microservices that come with metrics, logs, and a dashboard from day one. No Prometheus or Grafana required — but ready to integrate when your infrastructure catches up.

## Why observabilipy?

**The problem:** You're building a service but your org doesn't have centralized observability yet. Or you're deploying to client environments where you don't control the infrastructure. You still need to understand what your service is doing — and you don't want to wait for the platform team.

**The solution:** Develop your observability features decoupled from the observability stack:

- **Your code** defines metrics, logs, and dashboards
- **The infrastructure** (Prometheus, Grafana, Loki) is optional and can come later
- **Standard endpoints** (`/metrics`, `/logs`) work standalone and integrate seamlessly when infra arrives

This means you can ship observable services today. When central infrastructure catches up, just point scrapers at your existing endpoints — no code changes needed.

## Quick Start

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from observabilipy import (
    SQLiteLogStorage, SQLiteMetricsStorage,
    EmbeddedRuntime, RetentionPolicy, info, counter
)
from observabilipy.adapters.frameworks.fastapi import create_observability_router

# Storage with automatic retention
log_storage = SQLiteLogStorage("app.db")
metrics_storage = SQLiteMetricsStorage("app.db")
runtime = EmbeddedRuntime(
    log_storage=log_storage,
    metrics_storage=metrics_storage,
    log_retention=RetentionPolicy(max_age_seconds=86400),  # 24 hours
)

@asynccontextmanager
async def lifespan(app):
    await runtime.start()
    yield
    await runtime.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(create_observability_router(log_storage, metrics_storage))

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    await log_storage.write(info("User requested", user_id=user_id))
    await metrics_storage.write(counter("api_requests_total", endpoint="get_user"))
    return {"user_id": user_id}
```

Run it and you get:
- `GET /logs` — structured logs in NDJSON
- `GET /metrics/prometheus` — Prometheus text format
- `GET /metrics` — metrics in NDJSON (for custom dashboards)

## Use Cases

| Scenario | How observabilipy helps |
|----------|------------------------|
| **Decoupled development** | Build observability features without waiting for platform team to set up Prometheus/Grafana |
| **Internal tools & microservices** | Ship with observability included, no external dependencies required |
| **Client/on-prem deployments** | Works standalone in unknown environments, integrates when infrastructure exists |
| **Prototypes & MVPs** | Production-ready observability patterns from the start — no rework later |

## Features

- **Prometheus-compatible** — `/metrics/prometheus` endpoint, ready for scraping
- **Grafana Alloy/Loki compatible** — `/logs` endpoint in NDJSON format
- **Embedded dashboard** — Live charts and log viewer ([see example](examples/dashboard_example.py))
- **Persistent storage** — SQLite with WAL mode, logs survive restarts
- **Automatic retention** — Background cleanup with configurable policies
- **Framework support** — FastAPI, Django, ASGI, WSGI

## Installation

```bash
pip install observabilipy[fastapi]  # or [django]
```

## Recording Metrics and Logs

```python
from observabilipy import info, error, warn, counter, gauge, histogram

# Structured logs
await log_storage.write(info("User logged in", user_id=123, ip="10.0.0.1"))
await log_storage.write(error("Payment failed", order_id=456, reason="timeout"))

# Metrics
await metrics_storage.write(counter("requests_total", method="GET", status=200))
await metrics_storage.write(gauge("active_connections", value=42))
await metrics_storage.write(histogram("request_duration_seconds", value=0.125))
```

### Context Managers

```python
from observabilipy import timer, timed_log

# Auto-record timing to histogram
async with timer(metrics_storage, "request_duration_seconds", method="GET"):
    response = await handle_request()

# Log entry/exit with elapsed time
async with timed_log(log_storage, "Processing order", order_id=123):
    await process_order()
```

### Python Logging Integration

```python
import logging
from observabilipy import ObservabilipyHandler

logging.getLogger().addHandler(ObservabilipyHandler(log_storage))

# All logging calls now captured
logging.info("Starting up", extra={"version": "1.0.0"})
```

## Storage Options

| Backend | Use Case |
|---------|----------|
| `SQLiteLogStorage` / `SQLiteMetricsStorage` | **Recommended** — persistent, survives restarts |
| `InMemoryLogStorage` / `InMemoryMetricsStorage` | Development and testing |
| `RingBufferLogStorage` / `RingBufferMetricsStorage` | Memory-constrained environments |

## Embedded Dashboard

Build admin visibility into your service:

```bash
# Run the dashboard example
uvicorn examples.dashboard_example:app --reload
# Visit http://localhost:8000/
```

See [dashboard_example.py](examples/dashboard_example.py) for a complete implementation with live CPU/memory charts and log viewer.

## Integration with Central Infrastructure

When your org sets up Prometheus/Grafana, no code changes needed:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:8000']
    metrics_path: '/metrics/prometheus'
```

```yaml
# grafana-alloy config
loki.source.api "my_service" {
  http { listen_address = "0.0.0.0:3100" }
  forward_to = [loki.write.default.receiver]
}
```

## Examples

| Example | Description |
|---------|-------------|
| [dashboard_example.py](examples/dashboard_example.py) | Embedded admin dashboard with live charts |
| [fastapi_example.py](examples/fastapi_example.py) | Basic FastAPI setup |
| [sqlite_example.py](examples/sqlite_example.py) | Persistent storage |
| [logging_handler_example.py](examples/logging_handler_example.py) | Python logging integration |
| [embedded_runtime_example.py](examples/embedded_runtime_example.py) | Background retention cleanup |

## When to use observabilipy

| observabilipy | OpenTelemetry |
|---------------|---------------|
| No central infrastructure yet | Prometheus/Grafana/Jaeger already set up |
| Self-contained microservices | Distributed tracing across services |
| Simple, lightweight | Full CNCF observability stack |
| Works offline | Cloud-native environments |

They can coexist — use observabilipy for services not yet connected to central infrastructure.

## License

MIT
