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
- [ ] Build `EmbeddedRuntime` orchestrator (lifecycle, background thread)
- [ ] Unit tests for retention logic (pure, no threads)
- [ ] Integration tests for `EmbeddedRuntime` (with in-memory storage)
- [ ] Example usage in `examples/`

### Other
- [ ] E2E tests
- [ ] Documentation and README

## Phase 8: Developer Experience
- [x] Pre-commit hooks mirroring CI pipeline (ruff check, ruff format, mypy, pytest)

---

## Current Focus

**Phase 7: Runtime & Polish**

Next action: Create `RetentionPolicy` value object and retention logic in core.
