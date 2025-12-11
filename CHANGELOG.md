# Changelog

All notable changes to this project will be documented in this file.

## [0.5.1] - 2025-12-11

### Added
- Django adapter (`create_observability_urlpatterns`) for ASGI deployments
- Django example app (`examples/django_example.py`)
- Integration tests for Django adapter (7 tests)
- `django` optional dependency

## [0.5.0] - 2025-12-11

### Added
- SQLite storage adapters (`SQLiteLogStorage`, `SQLiteMetricsStorage`) using `aiosqlite`
- Integration tests for SQLite adapters (15 tests)
- `aiosqlite` dependency

## [0.4.2] - 2025-12-11

### Changed
- Convert encoders (`encode_logs`, `encode_metrics`) to async functions accepting `AsyncIterable`
- Simplify FastAPI adapter to pass async iterables directly to encoders

## [0.4.1] - 2025-12-11

### Added
- CHANGELOG.md for tracking version history
- Release tracking files convention in CLAUDE.md

### Changed
- Updated ROADMAP.md to reflect Phase 4 async progress

## [0.4.0] - 2025-12-11

### Changed
- Convert storage ports to async interfaces (`async def write`, `AsyncIterable` returns)
- Convert in-memory storage adapters to async generators
- Convert FastAPI endpoints to async handlers

### Added
- pytest-asyncio for async test support
- uvicorn dev dependency

## [0.3.0] - 2025-12-11

### Added
- Prometheus text format encoder
- FastAPI adapter with `/metrics` and `/logs` endpoints
- Integration tests for FastAPI endpoints
- Example app (`examples/fastapi_example.py`)

## [0.2.0] - 2025-12-11

### Added
- NDJSON encoder for logs

## [0.1.0] - 2025-12-11

### Added
- Core models (`LogEntry`, `MetricSample`)
- Port interfaces (`LogStoragePort`, `MetricsStoragePort`)
- In-memory storage adapters
- GitHub Actions CI workflow
