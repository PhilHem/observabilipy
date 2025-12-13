# Roadmap

## Phase 1: Core Foundation
- [x] Project setup (`pyproject.toml`, dev dependencies)
- [x] Pytest configuration with marks in `pyproject.toml`
- [x] GitHub Actions CI with separate jobs per mark
- [x] Core models (`LogEntry`, `MetricSample`)
- [x] Port interfaces (`LogStoragePort`, `MetricsStoragePort`)
- [x] In-memory storage adapters
- [x] Unit tests for models and in-memory storage

## Phase 2: Encoding
- [x] NDJSON encoder for logs
- [x] Prometheus text format encoder for metrics
- [x] Unit tests for encoders

## Phase 3: First Framework Adapter
- [x] FastAPI adapter with `/metrics` and `/logs` endpoints
- [x] Integration tests for FastAPI endpoints
- [x] Example app (`examples/fastapi_example.py`)

## Phase 4: Async Foundation
- [x] Convert ports to async (`async def read`, `async def write`, etc.)
- [x] Convert in-memory storage adapters to async
- [x] Convert encoders to accept `AsyncIterable`
- [x] Update FastAPI adapter to async endpoints
- [x] Add `pytest-asyncio`, update all tests to async
- [x] Update example app

## Phase 5: Persistent Storage
- [x] SQLite storage adapter (async with `aiosqlite`)
- [x] Integration tests for SQLite adapter

## Phase 6: Additional Adapters
- [x] Django adapter
- [x] ASGI generic adapter
- [x] Ring buffer storage adapter

## Phase 7: Runtime & Polish

### Embedded Mode
- [x] Add `delete_before(timestamp)` and `count()` to storage ports
- [x] Implement deletion methods in all storage adapters (in-memory, SQLite, ring buffer)
- [x] Create `RetentionPolicy` value object in core
- [x] Create pure retention logic functions in core
- [x] Build `EmbeddedRuntime` orchestrator (lifecycle, background thread)
- [x] Unit tests for retention logic (pure, no threads)
- [x] Integration tests for `EmbeddedRuntime` (with in-memory storage)

### Examples
- [x] `embedded_runtime_example.py` - EmbeddedRuntime with retention policies and SQLite
- [x] `sqlite_example.py` - Persistent storage with SQLite adapter
- [x] `ring_buffer_example.py` - Fixed-size memory storage for constrained environments

### Other
- [x] E2E tests (log pipeline, metrics pipeline, persistence, concurrency)
- [x] SQLite WAL mode for concurrent access
- [x] Documentation and README

## Phase 8: Developer Experience
- [x] Pre-commit hooks mirroring CI pipeline (ruff check, ruff format, mypy, pytest)

## Phase 9: Distribution
- [x] PyPI publishing setup (build configuration, classifiers)
- [x] GitHub Actions release workflow (publish on tag)
- [x] Test on TestPyPI first

## Phase 10: Ergonomics & Polish

### Type Safety
- [x] Add `py.typed` marker for type checker support
- [x] Custom exceptions with actionable error messages

### Configuration
- [x] Configuration validation (retention policies, buffer sizes)
- [x] Per-level retention policies (optional overrides per log level)

### Framework Adapters
- [x] Log level filtering on `/logs` endpoint (`?level=error`)
- [x] WSGI adapter (Flask, Bottle, etc.)

### API Ergonomics
- [x] Metric helper functions (`counter()`, `gauge()`, `histogram()`)
- [x] Export `DEFAULT_HISTOGRAM_BUCKETS` constant from package root
- [x] `timer()` context manager for histogram (auto-records elapsed time)
- [x] Log helper function `log(level, message, **attributes)`
- [x] Level-specific log helpers: `info()`, `error()`, `debug()`, `warn()`
- [x] `timed_log()` context manager (logs entry/exit with elapsed time)
- [x] `log_exception()` helper (captures exception info and traceback)
- [x] Re-export common symbols from root `__init__.py` for simpler imports
- [x] Rename package directory from `observability/` to `observabilipy/` (match PyPI name)

## Phase 11: API Redesign

Unify storage and HTTP API design for consistency and clarity.

### 11.1 Storage Port Interface

**Add `read(since)` to MetricsStoragePort:**
- [x] Add `read(since: float = 0) -> AsyncIterable[MetricSample]` to `MetricsStoragePort` protocol
- [x] Implement `read(since)` in `InMemoryMetricsStorage`
- [x] Implement `read(since)` in `SQLiteMetricsStorage` (add index on timestamp)
- [x] Implement `read(since)` in `RingBufferMetricsStorage`
- [x] Add unit tests for `read(since)` in all storage adapters

**Deprecate and remove `scrape()`:**
- [x] Mark `scrape()` as deprecated (keep for one release)
- [x] Update all internal usage to use `read()` instead
- [x] Remove `scrape()` in next major version

### 11.2 Encoding Layer

**Add `encode_current()` for Prometheus:**
- [x] Add `encode_current(samples: AsyncIterable[MetricSample]) -> str` to `core/encoding/prometheus.py`
- [x] Logic: keep only latest sample per (name, labels) combination
- [x] Unit tests for `encode_current()` with multiple samples per metric

**Add NDJSON encoding for metrics:**
- [x] Add `encode_ndjson(samples: AsyncIterable[MetricSample]) -> str` to `core/encoding/ndjson.py`
- [x] Add `encode_ndjson_sync(samples: Iterable[MetricSample]) -> str` for sync adapters

### 11.3 HTTP API - Framework Adapters

**FastAPI adapter (`adapters/frameworks/fastapi.py`):**
- [x] Update `GET /logs` to accept `?since=` query param, return NDJSON
- [x] Update `GET /metrics` to accept `?since=` query param, return NDJSON
- [x] Add `GET /metrics/prometheus` endpoint using `encode_current()`
- [x] Integration tests for all three endpoints

**Django adapter (`adapters/frameworks/django.py`):**
- [x] Update `/logs/` to accept `?since=` query param, return NDJSON
- [x] Update `/metrics/` to accept `?since=` query param, return NDJSON
- [x] Add `/metrics/prometheus/` endpoint using `encode_current()`
- [x] Integration tests for all three endpoints

**ASGI adapter (`adapters/frameworks/asgi.py`):**
- [x] Update `/logs` to accept `?since=` query param, return NDJSON
- [x] Update `/metrics` to accept `?since=` query param, return NDJSON
- [x] Add `/metrics/prometheus` endpoint using `encode_current()`
- [x] Integration tests for all three endpoints

**WSGI adapter (`adapters/frameworks/wsgi.py`):**
- [x] Update `/logs` to accept `?since=` query param, return NDJSON
- [x] Update `/metrics` to accept `?since=` query param, return NDJSON
- [x] Add `/metrics/prometheus` endpoint using `encode_current()`
- [x] Integration tests for all three endpoints

### 11.4 Examples & Documentation

- [x] Update `dashboard_example.py` to use `/metrics?since=` with NDJSON parsing
- [x] Fix `dashboard_example.py` metrics display with Browser
- [x] Update `fastapi_example.py` to demonstrate new endpoints
- [x] Update README with new API documentation

---

## Future: API Ergonomics

Ideas for improving developer experience. To be prioritized later.

### Instrumentation Decorators
- [x] `@instrument` decorator for automatic request metrics (counter + timer)
- [x] Configurable metric names and labels via decorator arguments
- [x] Framework-specific variants (FastAPI dependency, Django decorator)

### Python Logging Integration
- [x] `ObservabilipyHandler` - logging handler that writes to `LogStoragePort`
- [x] Automatic attribute extraction from `LogRecord` (module, funcName, lineno)
- [x] Optional structured context via `context_provider` callback and `log_context()` helper
- [x] Export `ContextProvider` type alias from package root for user type hints
- [x] Example showing `log_context` with FastAPI middleware (request ID injection)

### Async-Aware ObservabilipyHandler

Make `ObservabilipyHandler` work inside existing async event loops (e.g., FastAPI TestClient).
~~Currently `emit()` uses `asyncio.run()` which fails when nested in a running loop.~~

**TDD Cycle 1: Detect running event loop** ✅
- [x] Write test: `emit()` works when no event loop is running (current behavior)
- [x] Write test: `emit()` works when called from inside a running event loop
- [x] Implement: detect running loop with `asyncio.get_running_loop()`, use `loop.create_task()` or queue

**TDD Cycle 2: Background writer thread (optional fallback)** ✅
- [x] Write test: logs are written even when event loop is busy
- [x] Write test: handler shutdown flushes pending writes
- [x] Implement: optional background thread with queue for fire-and-forget writes
- [x] Add `flush()` method that blocks until queue is drained (uses `queue.join()`)

**TDD Cycle 3: Integration with FastAPI TestClient** ✅
- [x] Write test: `ObservabilipyHandler` works with FastAPI `TestClient` and middleware
- [x] Write test: `log_context` attributes appear in logs during TestClient requests
- [x] Update `test_middleware_log_context.py` to use actual TestClient instead of simulation

### Documentation & Discoverability
- [x] Module-level docstring in `__init__.py` with quickstart example
- [x] Inline docstring examples for all public functions

### Doctest Infrastructure
- [x] Async encoding docstring examples (`encode_logs`, `encode_ndjson`, `encode_metrics`, `encode_current`)

---

## v1.x Complete ✓

Phases 1-11 complete. The library provides a solid foundation for standalone observability with logs, metrics, multiple storage backends, and framework adapters.

---

# v2.0.0: Standalone Experience & Integration Ready

**Core positioning:** Observability without the infrastructure. Works standalone today, integrates with central infrastructure when available.

v2.0 priorities:
1. Make standalone mode genuinely useful (built-in dashboard, CLI)
2. Enable sync to central infrastructure (push exporters, OTLP)
3. Keep it simple — avoid feature creep

---

## Phase 12: Dashboard Integration Guides

Provide integration patterns for embedding observabilipy data into existing dashboards using established charting libraries. We expose standard endpoints; users choose their visualization tools.

### 12.1 Documentation

- [ ] Integration guide: Chart.js with `chartjs-plugin-datasource-prometheus`
- [ ] Integration guide: Using `/metrics?since=` NDJSON with vanilla JS
- [ ] Integration guide: Log viewer component patterns (polling, incremental fetch)
- [ ] Integration guide: Embedding in React admin dashboards
- [ ] Integration guide: Embedding in Django admin

### 12.2 Example Patterns

- [ ] `examples/chartjs_dashboard.html` — standalone HTML using Chart.js + prometheus plugin
- [ ] `examples/react_dashboard/` — minimal React app with metrics chart and log table
- [ ] `examples/django_admin_integration.py` — adding observabilipy widgets to Django admin

### 12.3 JSON API Improvements

- [ ] Add `/metrics/json` endpoint (structured JSON instead of NDJSON for easier JS consumption)
- [ ] Add `/logs/json` endpoint (array format for simpler frontend parsing)
- [ ] Pagination support (`?limit=` and `?offset=`) for log endpoints
- [ ] Integration tests for new endpoints

---

## Phase 13: CLI Tools

Local debugging without a browser.

### 13.1 Core CLI

- [ ] `observabilipy` CLI entry point (using `click` or `typer`)
- [ ] `observabilipy tail <url>` — stream logs from `/logs` endpoint
- [ ] `observabilipy metrics <url>` — show current metrics from `/metrics/prometheus`
- [ ] `--level` filter for tail command
- [ ] `--follow` mode with polling
- [ ] Unit tests for CLI

### 13.2 SQLite Direct Access

- [ ] `observabilipy query <db-path>` — query SQLite storage directly
- [ ] `--since`, `--level`, `--limit` filters
- [ ] JSON and table output formats
- [ ] Integration tests

### 13.3 Optional: TUI Dashboard

- [ ] Terminal UI using `rich` or `textual`
- [ ] Live-updating metrics display
- [ ] Log viewer with scrolling
- [ ] Integration tests

---

## Phase 14: Push Exporters

Sync to central infrastructure when it becomes available.

### 14.1 Exporter Port

- [ ] Define `ExporterPort` protocol in `core/ports.py`
  - `export_logs(logs: AsyncIterable[LogEntry]) -> None`
  - `export_metrics(metrics: AsyncIterable[MetricSample]) -> None`
- [ ] Unit tests for exporter interface

### 14.2 HTTP Push Exporters

- [ ] Prometheus Pushgateway exporter (`adapters/exporters/pushgateway.py`)
- [ ] Grafana Loki push exporter (for logs)
- [ ] Generic HTTP/JSON exporter (configurable endpoint)
- [ ] Integration tests with mock HTTP server

### 14.3 OTLP Exporter

- [ ] OTLP/HTTP exporter for logs (`adapters/exporters/otlp.py`)
- [ ] OTLP/HTTP exporter for metrics
- [ ] JSON encoding (no protobuf dependency by default)
- [ ] Optional `opentelemetry-proto` extra for binary encoding
- [ ] Integration tests

### 14.4 Background Export Runtime

- [ ] Add `exporters` parameter to `EmbeddedRuntime`
- [ ] Add `export_interval` option (default: 60 seconds)
- [ ] Background task that periodically pushes to configured exporters
- [ ] Configurable batch sizes
- [ ] Retry with exponential backoff on failure
- [ ] Unit tests for export scheduling

---

## Phase 15: Operational Polish

Production-readiness improvements.

### 15.1 Health Endpoint

- [ ] Add `/health` endpoint to all framework adapters
- [ ] Storage connectivity checks
- [ ] Configurable health check logic (custom checks)
- [ ] Return JSON with component status
- [ ] Integration tests

### 15.2 Gzip Compression

- [ ] Gzip compression for `/logs` and `/metrics` responses
- [ ] `Accept-Encoding` header detection
- [ ] Configurable (enabled by default)
- [ ] Integration tests

### 15.3 Request Metrics Middleware

- [ ] Optional middleware that auto-records request metrics
- [ ] `http_requests_total` counter with method, path, status labels
- [ ] `http_request_duration_seconds` histogram
- [ ] FastAPI, Django, ASGI, WSGI variants
- [ ] Integration tests

---

## Future Ideas (Post v2.0)

To be considered after v2.0 is stable. These are lower priority given the core positioning.

### Tracing (if needed)

- `Span` model with W3C Trace Context compatible IDs
- Span storage adapters
- `@traced` decorator
- `/traces` endpoint
- OTLP trace export

*Note: Most users without central infrastructure aren't doing distributed tracing. Add this only if there's clear demand.*

### Enhanced Metrics

- Typed metrics (Counter, Gauge, Histogram as distinct types)
- Metric registry for pre-declaration
- Histogram aggregation and quantiles

### Streaming

- WebSocket endpoints for live updates
- Server-Sent Events (SSE) alternative
- `subscribe()` method on storage ports

### Remote Storage

- Redis storage adapter
- PostgreSQL storage adapter

---

## Current Focus

**v1.x complete.** Starting v2.0.0.

Next step: Phase 12.1 (Dashboard integration documentation)
