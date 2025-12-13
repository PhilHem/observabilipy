# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python library providing **metrics** and **structured log** collection with:
- Hexagonal architecture (pure core, ports, adapters)
- Framework-agnostic integration (FastAPI, Django, ASGI, WSGI)
- NDJSON log endpoints for Grafana Alloy compatibility
- Prometheus-style metrics endpoints
- Optional embedded mode with SQLite storage

## Build Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run single test
uv run pytest tests/unit/test_models.py::test_log_entry -v

# Type checking
uv run mypy src/observabilipy/

# Linting
uv run ruff check src/observabilipy/
uv run ruff format src/observabilipy/
```

### Package Management (uv only)

**Never edit `pyproject.toml` dependencies directly.** Always use uv commands:

```bash
uv add requests              # Add dependency
uv add --dev pytest          # Add dev dependency
uv remove requests           # Remove dependency
uv lock                      # Update lock file
```

Ruff configuration lives in `pyproject.toml` under `[tool.ruff]`.

### Version Bumping

When bumping the version in `pyproject.toml`, always run `uv lock` afterward to update the lock file:

```bash
# After editing version in pyproject.toml
uv lock
```

### Release Tracking Files

This project uses `CHANGELOG.md` and `ROADMAP.md` to track changes:
- **CHANGELOG.md** - Version history with changes per release
- **ROADMAP.md** - Development phases and progress

Before releasing, check if these files need updates based on commits since last tag.

## Architecture

```
              +-----------------------+
              |   Framework Adapters  |
  HTTP <----> |  (FastAPI, Django)    |
              +-----------------------+
                         ^
                         |
              +-----------------------+
              |      Core Domain      |
              |  Models & Services    |
              +-----------------------+
                         |
                         v
              +-----------------------+
              |   Storage Adapters    |
              | (SQLite, Memory, etc) |
              +-----------------------+
```

### Core (`observabilipy/core/`)
- **Pure Python only** - no framework imports, no I/O, no SQLite/file/network access
- Contains: data models, ports (Protocol interfaces), domain services, encoding logic
- Models: `LogEntry` (timestamp, level, message, attributes) and `MetricSample` (name, timestamp, value, labels)

### Ports (`observabilipy/core/ports.py`)
```python
class LogStoragePort(Protocol):
    def write(self, entry: LogEntry) -> None: ...
    def read(self, since: float = 0) -> Iterable[LogEntry]: ...

class MetricsStoragePort(Protocol):
    def write(self, sample: MetricSample) -> None: ...
    def read(self, since: float = 0) -> Iterable[MetricSample]: ...
```

### Adapters (`observabilipy/adapters/`)
- **Storage**: `sqlite.py`, `in_memory.py`, `ring_buffer.py`
- **Frameworks**: `fastapi.py`, `django.py`, `asgi.py`
- **Exporters**: `prometheus.py` (text format), `alloy.py` (NDJSON)

### Encoding (`observabilipy/core/encoding/`)
- `ndjson.py` - Encode logs to newline-delimited JSON
- `prometheus.py` - Encode metrics to Prometheus text format

### Runtime (`observabilipy/runtime/`)
- `embedded_mode.py` - Background ingestion, retention policies for standalone operation

## Folder Structure

```
src/observabilipy/
├── __init__.py          # Re-exports common symbols for convenient imports
├── core/
│   ├── models.py
│   ├── services.py
│   ├── ports.py
│   └── encoding/
│       ├── ndjson.py
│       └── prometheus.py
├── adapters/
│   ├── storage/
│   │   ├── sqlite.py
│   │   ├── in_memory.py
│   │   └── ring_buffer.py
│   ├── frameworks/
│   │   ├── fastapi.py
│   │   ├── django.py
│   │   └── asgi.py
│   └── exporters/
│       ├── prometheus.py
│       └── alloy.py
└── runtime/
    └── embedded_mode.py
examples/
├── fastapi_example.py
└── django_example.py
tests/
├── unit/
├── integration/
└── e2e/
```

## Key Constraints

1. Core must never import framework or I/O code
2. Adapters implement Port protocols
3. Framework adapters expose `/metrics` and `/logs` endpoints
4. Logs export as NDJSON, metrics as Prometheus text format

## Balancing Abstraction vs Coupling

Hexagonal architecture can lead to over-engineering. Use these indicators:

### Signs of unnecessary indirection
- A port with only one adapter that will never have another
- Wrapper classes that just delegate to another class
- Interfaces with a single method that could be a function
- "Manager", "Handler", "Processor" classes that don't manage state
- More than 3 layers between HTTP request and storage

### Signs of problematic coupling
- Core importing from `adapters/`
- Storage adapter importing a web framework
- Tests requiring a database or network to run
- Changing a model requires updating more than 3 files

### Rules of thumb
- **No port without 2+ adapters** (or clear intent for future adapters)
- **Prefer functions over classes** for stateless operations (encoders)
- **Adapters should be thin** - convert types and delegate, not implement logic
- **If unsure, start concrete** - extract abstraction when the second use case appears

## Development Workflow (TDD)

This architecture is designed for test-driven development. Always write tests first:

1. **Define the port interface** in `core/ports.py`
2. **Write failing tests** against the port using in-memory adapters
3. **Implement core logic** until tests pass
4. **Add real adapters** (SQLite, FastAPI) that satisfy the same port

The in-memory adapters are not test doubles - they're production-ready implementations. Unit tests use them directly, keeping tests fast and deterministic.

### Planning Review

After completing any significant implementation, review for roadmap opportunities:

1. **Read ROADMAP.md first** to understand current phases, existing items, and future directions - suggestions must NOT duplicate anything already listed

2. **Identify 3 quick wins** that:
   - Build directly on what was just implemented
   - Are small in scope (1-2 TDD cycles)
   - Complete a natural workflow or fill an obvious gap
   - Are NOT already in the roadmap (check all phases including Future)

3. **Present to user** before adding to `ROADMAP.md`

4. **Use `/update-roadmap`** command to trigger this review

This keeps the roadmap fresh with achievable next steps that leverage recent work.

### Test Organization

- **Unit tests** (`tests/unit/`): Core only, use `InMemoryLogStorage`/`InMemoryMetricsStorage`, no I/O
- **Integration tests** (`tests/integration/`): Test adapters (SQLite, framework endpoints, encoders)
- **E2E tests** (`tests/e2e/`): Full app with real framework and scrape endpoints

### Pytest Marks & CI

Tests are marked by architectural component for separate GitHub Actions jobs:

```python
@pytest.mark.core        # Core models, ports, services
@pytest.mark.encoding    # NDJSON, Prometheus encoders
@pytest.mark.storage     # Storage adapters (sqlite, in_memory, ring_buffer)
@pytest.mark.fastapi     # FastAPI framework adapter
@pytest.mark.django      # Django framework adapter
@pytest.mark.e2e         # End-to-end tests
```

Run specific components:
```bash
pytest -m core
pytest -m "storage and not sqlite"  # in-memory only
pytest -m fastapi
```

CI runs each mark as a separate job for clear failure isolation.

### CI Parity

**CI must use identical commands to local development.** No separate CI-specific scripts or logic. The GitHub Actions workflow uses `uv sync` and `uv run` exactly as developers do locally. This ensures:
- What passes locally passes in CI
- No "works on my machine" issues
- Single source of truth for how to run tests

### Pre-commit Hooks

Pre-commit hooks mirror the CI pipeline to catch issues before they reach CI. The hooks run:
1. `ruff check` - Linting
2. `ruff format --check` - Format verification
3. `mypy` - Type checking
4. `pytest` - Tests

Install hooks with:
```bash
uv run pre-commit install
```

Run manually:
```bash
uv run pre-commit run --all-files
```

The hooks use the same commands as CI, maintaining parity between local development, pre-commit, and CI.

## Testing Async Code

### SQLite Storage Tests

The SQLite storage adapters use `asyncio.Lock` for thread-safe initialization. To avoid pytest-asyncio event loop issues:

1. **Lazy lock creation**: The `_init_lock` is created lazily via `_get_lock()` rather than at `__init__` time, preventing locks from being bound to the wrong event loop.

2. **Proper cleanup for `:memory:` databases**: Tests using `:memory:` databases must use fixtures that call `close()` after the test:

```python
@pytest.fixture
async def memory_log_storage() -> AsyncGenerator[SQLiteLogStorage]:
    storage = SQLiteLogStorage(":memory:")
    yield storage
    await storage.close()
```

Without proper cleanup, persistent connections remain open and can cause tests to hang.

## Extending the System

### Adding a Storage Backend
1. Create module in `adapters/storage/`
2. Implement `LogStoragePort` and/or `MetricsStoragePort`
3. Write integration tests

### Adding a Web Framework
1. Create router/blueprint/view in `adapters/frameworks/`
2. Expose `/metrics` and `/logs` endpoints
3. Import only core and storage adapter - convert framework types to core types

### Adding an Exporter Format
1. Create adapter that transforms core primitives to external format
2. Place in `adapters/exporters/` or `core/encoding/` depending on purity

## Goals & Non-Goals

### Goals
- Easy integration with small embedded services and large apps
- FastAPI and Django support
- SQLite for offline log consumption
- Clean NDJSON endpoints for Alloy
- Minimal external dependencies

### Non-Goals
- Not a full Prometheus client library
- Not an opinionated logging framework
- Not a replacement for existing observability stacks
- No distributed message queue responsibilities

## Future Directions

- Configurable retention policies for logs
- Batch ingestion endpoints (bulk NDJSON)
- Streaming endpoints (HTTP chunked responses)
- WebSocket adapters
- Compression-aware SQLite ingestion
