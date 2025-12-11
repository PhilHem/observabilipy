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
- [ ] Log level filtering on `/logs` endpoint (`?level=error`)
- [ ] WSGI adapter (Flask, Bottle, etc.)

### API Ergonomics
- [ ] Metric helper functions (`counter()`, `gauge()`, `histogram()`)
- [x] Re-export common symbols from root `__init__.py` for simpler imports
- [x] Rename package directory from `observability/` to `observabilipy/` (match PyPI name)

---

## Current Focus

**Phase 10: Ergonomics & Polish**

Next action: Add metric helper functions or framework improvements.
