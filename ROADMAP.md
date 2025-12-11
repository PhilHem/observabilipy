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
- [ ] SQLite storage adapter (async with `aiosqlite`)
- [ ] Integration tests for SQLite adapter

## Phase 6: Additional Adapters
- [ ] Django adapter
- [ ] ASGI generic adapter
- [ ] Ring buffer storage adapter

## Phase 7: Runtime & Polish
- [ ] Embedded mode (background ingestion, retention)
- [ ] E2E tests
- [ ] Documentation and README

---

## Current Focus

**Phase 5: Persistent Storage**

Next action: Implement SQLite storage adapter with `aiosqlite`.
