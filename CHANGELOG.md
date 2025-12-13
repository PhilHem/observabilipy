# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-12-13

### Added
- Instrumentation decorators (`@timed`, `@counted`, `@timed_with_histogram`) for automatic metrics collection
- `ObservabilipyHandler` - Python `logging.Handler` integration for capturing logs to observabilipy storage
- Async-aware logging handler that properly handles both sync and async contexts
- `context_provider` and `log_context()` for structured context in middleware
- Doctest examples for all public functions
- Quickstart example in module docstring

## [1.0.0] - 2025-12-13

### Breaking Changes
- **BREAKING**: Removed `scrape()` method from `MetricsStoragePort` protocol and all storage adapters
  - Use `read()` instead, which provides identical functionality with optional `since` parameter for timestamp filtering
  - Migration: Replace `storage.scrape()` with `storage.read()`

### Added
- `log_exception()` helper for capturing exception info and traceback
- `timed_log()` context manager for logging entry/exit with elapsed time
- Level-specific log helpers: `info()`, `error()`, `debug()`, `warn()`

## [0.15.0] - 2025-12-13

### Added
- `log()` helper function for creating LogEntry objects with automatic timestamp

## [0.11.0] - 2025-12-12

### Added
- `level` query parameter on `/logs` endpoint for filtering logs by level (FastAPI, Django, ASGI adapters)
- `level` parameter on `LogStoragePort.read()` for level-based filtering at storage layer
- Level filtering implemented in all storage adapters (InMemory, SQLite, RingBuffer)

### Fixed
- pytest-asyncio session cleanup hangs by adding `asyncio_default_fixture_loop_scope` config
- Unclosed httpx.AsyncClient in e2e tests

## [0.10.2] - 2025-12-12

### Fixed
- SQLite storage adapters now use lazy `asyncio.Lock` creation to prevent event loop binding issues with pytest-asyncio
- Tests using `:memory:` databases now properly close connections to prevent hanging pytest processes

## [0.10.1] - 2025-12-11

### Fixed
- SQLite storage adapters now work with `:memory:` databases by maintaining a persistent connection

## [0.10.0] - 2025-12-11

### Added
- `LevelRetentionPolicy` for per-level log retention (e.g., keep ERROR logs 30 days, DEBUG logs 1 day)
- Level-aware methods on `LogStoragePort`: `delete_by_level_before()`, `count_by_level()`
- Level-aware retention logic: `calculate_level_age_threshold()`, `should_delete_by_level_count()`
- `EmbeddedRuntime` now accepts both `RetentionPolicy` and `LevelRetentionPolicy` (backward compatible)
- SQLite composite index on `(level, timestamp)` for efficient per-level queries

## [0.9.0] - 2025-12-11

### Changed
- **BREAKING**: Renamed package directory from `observability/` to `observabilipy/` to match PyPI package name
- Import path changed from `from observability import ...` to `from observabilipy import ...`

### Added
- Root `__init__.py` re-exports common symbols for simpler imports
- Users can now import directly: `from observabilipy import LogEntry, InMemoryLogStorage`

## [0.8.3] - 2025-12-11

### Added
- Custom exceptions (`ObservabilityError`, `ConfigurationError`) with actionable error messages
- `py.typed` marker for type checker support
- Validation for `RetentionPolicy` (rejects non-positive `max_age_seconds` and `max_count`)

## [0.8.2] - 2025-12-11

### Added
- PyPI publishing setup (classifiers, keywords, license, project URLs)
- MIT LICENSE file
- GitHub Actions release workflow for publishing to TestPyPI and PyPI
- `build` dev dependency

### Fixed
- CI e2e tests when fastapi not installed

## [0.8.1] - 2025-12-11

### Added
- `embedded_runtime_example.py` - EmbeddedRuntime with SQLite and retention policies
- `sqlite_example.py` - Persistent storage with SQLite adapter
- `ring_buffer_example.py` - Fixed-size memory storage for constrained environments
- `.gitignore` entries for `.db` files and `.history/`

## [0.8.0] - 2025-12-11

### Added
- `EmbeddedRuntime` orchestrator for background retention cleanup
- `RetentionPolicy` value object supporting age-based and count-based retention
- Pure retention logic functions (`calculate_age_threshold`, `should_delete_by_count`)
- `count()` and `delete_before(timestamp)` methods to storage ports
- Retention methods implemented in all storage adapters (in-memory, SQLite, ring buffer)

## [0.7.2] - 2025-12-11

### Changed
- Break down embedded mode into detailed implementation steps in roadmap

## [0.7.1] - 2025-12-11

### Changed
- Enable CI test jobs for encoding, storage, fastapi, and django (previously commented out)

## [0.7.0] - 2025-12-11

### Added
- Ring buffer storage adapters (`RingBufferLogStorage`, `RingBufferMetricsStorage`)
- Bounded in-memory storage with automatic eviction of oldest entries
- Uses `collections.deque(maxlen=...)` for O(1) writes with fixed memory footprint
- Unit tests for ring buffer adapters (13 tests)

## [0.5.5] - 2025-12-11

### Fixed
- CI typecheck job now installs fastapi extra so mypy can properly type-check the FastAPI adapter

## [0.5.4] - 2025-12-11

### Fixed
- Mypy errors for FastAPI adapter by adding `ignore_missing_imports` override for optional fastapi dependency

## [0.5.3] - 2025-12-11

### Fixed
- CI failures when running marker-filtered tests (e.g., `pytest -m storage`) by using `pytest.importorskip()` for optional framework dependencies
- Added ruff per-file-ignores for E402 in tests to support the importorskip pattern

## [0.5.2] - 2025-12-11

### Added
- Pre-commit hooks mirroring CI pipeline (ruff check, ruff format, mypy, pytest)
- `pre-commit` dev dependency

### Fixed
- Ruff linting issues in tests (type parameter syntax, import sorting)

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
