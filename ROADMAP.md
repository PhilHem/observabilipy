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
- [ ] NDJSON encoder for logs
- [ ] Prometheus text format encoder for metrics
- [ ] Unit tests for encoders

## Phase 3: First Framework Adapter
- [ ] FastAPI adapter with `/metrics` and `/logs` endpoints
- [ ] Integration tests for FastAPI endpoints
- [ ] Example app (`examples/fastapi_example.py`)

## Phase 4: Persistent Storage
- [ ] SQLite storage adapter
- [ ] Integration tests for SQLite adapter

## Phase 5: Additional Adapters
- [ ] Django adapter
- [ ] ASGI generic adapter
- [ ] Ring buffer storage adapter

## Phase 6: Runtime & Polish
- [ ] Embedded mode (background ingestion, retention)
- [ ] E2E tests
- [ ] Documentation and README

---

## Current Focus

**Phase 2: Encoding**

Next action: Implement NDJSON encoder for logs.
