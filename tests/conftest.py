"""Shared test fixtures for all test modules."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

try:
    import httpx
except ImportError:
    httpx = None


@pytest.fixture
def log_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for log storage tests."""
    return str(tmp_path / "logs.db")


@pytest.fixture
def metrics_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for metrics storage tests."""
    return str(tmp_path / "metrics.db")


# Aliases for e2e tests that use sqlite_* prefix naming
@pytest.fixture
def sqlite_log_db_path(log_db_path: str) -> str:
    """Alias for log_db_path (used by e2e tests)."""
    return log_db_path


@pytest.fixture
def sqlite_metrics_db_path(metrics_db_path: str) -> str:
    """Alias for metrics_db_path (used by e2e tests)."""
    return metrics_db_path


# === ASGI Test Fixtures ===


@pytest.fixture
def basic_asgi_app():
    """Basic ASGI app fixture that returns 200 OK.

    Used in tests to replace repeated inline ASGI app definitions.
    """
    from observabilipy.adapters.frameworks.asgi import Receive, Scope, Send

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        """Simple ASGI app that returns 200 OK."""
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    return app


@pytest.fixture
def asgi_scope():
    """Factory fixture for creating ASGI scope dicts.

    Used in tests to create scope dicts with customizable method/path.
    """
    from observabilipy.adapters.frameworks.asgi import Scope

    def _scope(method: str = "GET", path: str = "/test") -> Scope:
        return {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": [],
        }

    return _scope


@pytest.fixture
def asgi_send_capture():
    """Fixture that returns a send callable and a responses list for capture.

    Returns a tuple of (send_func, responses_list) for recording ASGI messages.
    Used in tests to replace repeated inline send/responses implementations.
    """

    responses: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        """Capture ASGI messages."""
        responses.append(message)

    return send, responses


@pytest.fixture
def asgi_test_client():
    """Factory fixture that creates an httpx.AsyncClient for ASGI testing.

    Returns a callable that accepts an ASGI app and yields a client
    with ASGITransport configured. This eliminates repeated inline
    AsyncClient setup in tests.

    Usage:
        async def test_something(asgi_test_client):
            app = create_asgi_app(log_storage, metrics_storage)
            async with asgi_test_client(app) as client:
                response = await client.get("/endpoint")
    """
    if httpx is None:
        pytest.skip("httpx not installed")

    def _get_client(app):
        """Return an AsyncClient context manager for the given app."""
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )

    return _get_client


# === Shared ASGI Storage Fixtures ===


@pytest.fixture
async def log_storage() -> AsyncGenerator:
    """Fixture providing an empty log storage for ASGI tests."""
    from observabilipy.adapters.storage.in_memory import InMemoryLogStorage

    return InMemoryLogStorage()


@pytest.fixture
async def metrics_storage() -> AsyncGenerator:
    """Fixture providing an empty metrics storage for ASGI tests."""
    from observabilipy.adapters.storage.in_memory import InMemoryMetricsStorage

    return InMemoryMetricsStorage()


@pytest.fixture
async def asgi_client_with_storage(
    log_storage,
    metrics_storage,
    asgi_test_client,
):
    """Fixture combining storage and ASGI test client.

    Returns a tuple of (client, log_storage, metrics_storage) for convenient
    access in tests. This reduces boilerplate in test methods that need to
    create an app and make requests.

    Usage:
        async def test_something(asgi_client_with_storage):
            client, log_storage, metrics_storage = asgi_client_with_storage
            response = await client.get("/endpoint")
            # log_storage and metrics_storage available if needed for setup
    """
    if httpx is None:
        pytest.skip("httpx not installed")

    from observabilipy.adapters.frameworks.asgi import create_asgi_app

    app = create_asgi_app(log_storage, metrics_storage)
    async with asgi_test_client(app) as client:
        yield client, log_storage, metrics_storage


# === WSGI Test Fixtures ===


@pytest.fixture
def wsgi_test_client():
    """Factory fixture that creates an httpx.Client for WSGI testing.

    Returns a callable that accepts a WSGI app and yields a client
    with WSGITransport configured. This eliminates repeated inline
    Client setup in tests.

    Usage:
        def test_something(wsgi_test_client):
            app = create_wsgi_app(log_storage, metrics_storage)
            with wsgi_test_client(app) as client:
                response = client.get("/endpoint")
    """
    if httpx is None:
        pytest.skip("httpx not installed")

    def _get_client(app):
        """Return a Client context manager for the given app."""
        return httpx.Client(
            transport=httpx.WSGITransport(app=app), base_url="http://test"
        )

    return _get_client


@pytest.fixture
def wsgi_client_with_storage(
    log_storage,
    metrics_storage,
    wsgi_test_client,
):
    """Fixture combining storage and WSGI test client.

    Returns a tuple of (client, log_storage, metrics_storage) for convenient
    access in tests. This reduces boilerplate in test methods that need to
    create an app and make requests.

    Usage:
        def test_something(wsgi_client_with_storage):
            client, log_storage, metrics_storage = wsgi_client_with_storage
            response = client.get("/endpoint")
            # log_storage and metrics_storage available if needed for setup
    """
    if httpx is None:
        pytest.skip("httpx not installed")

    from observabilipy.adapters.frameworks.wsgi import create_wsgi_app

    app = create_wsgi_app(log_storage, metrics_storage)
    with wsgi_test_client(app) as client:
        yield client, log_storage, metrics_storage
