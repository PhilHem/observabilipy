"""Integration tests for ASGI error handling and routing."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest

from observabilipy.adapters.frameworks.asgi import create_asgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)


@asynccontextmanager
async def mock_encoder(encoder_name: str, failing_encoder: Callable[..., Any]):
    """Context manager for temporarily replacing an encoder with a failing one.

    Args:
        encoder_name: Name of the encoder function to mock (e.g., 'encode_ndjson')
        failing_encoder: Callable that raises an exception

    Yields:
        None

    Example:
        async with mock_encoder('encode_ndjson', failing_encode):
            response = await client.get("/metrics")
    """
    import observabilipy.adapters.frameworks.asgi as asgi_module

    original = getattr(asgi_module, encoder_name)
    setattr(asgi_module, encoder_name, failing_encoder)

    try:
        yield
    finally:
        setattr(asgi_module, encoder_name, original)


class TestASGIErrorHandling:
    """Tests for error handling in endpoints."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_metrics_endpoint_handles_encoding_error_gracefully(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics handles encoding errors gracefully with 500."""
        app = create_asgi_app(log_storage, metrics_storage)

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Encoding failed")

        async with mock_encoder("encode_ndjson", failing_encode):
            async with asgi_test_client(app) as client:
                response = await client.get("/metrics")

            assert response.status_code == 500
            assert "error" in response.text.lower()

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_logs_endpoint_handles_encoding_error_gracefully(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs handles encoding errors gracefully with 500."""
        app = create_asgi_app(log_storage, metrics_storage)

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Encoding failed")

        async with mock_encoder("encode_logs", failing_encode):
            async with asgi_test_client(app) as client:
                response = await client.get("/logs")

            assert response.status_code == 500
            assert "error" in response.text.lower()

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_metrics_endpoint_error_does_not_expose_details(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics error response does not expose error details."""
        app = create_asgi_app(log_storage, metrics_storage)

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Sensitive database connection error: db://prod")

        async with mock_encoder("encode_ndjson", failing_encode):
            async with asgi_test_client(app) as client:
                response = await client.get("/metrics")

            assert response.status_code == 500
            # Error details must not be exposed
            assert "Sensitive database connection error" not in response.text
            assert "db://prod" not in response.text
            # Should contain generic message
            assert "Internal Server Error" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_logs_endpoint_error_does_not_expose_details(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs error response does not expose error details."""
        app = create_asgi_app(log_storage, metrics_storage)

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Sensitive API key: secret_xyz789")

        async with mock_encoder("encode_logs", failing_encode):
            async with asgi_test_client(app) as client:
                response = await client.get("/logs")

            assert response.status_code == 500
            # Error details must not be exposed
            assert "Sensitive API key" not in response.text
            assert "secret_xyz789" not in response.text
            # Should contain generic message
            assert "Internal Server Error" in response.text


class TestASGIRouting:
    """Tests for routing and error handling."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.RoutingUnknownPath")
    @pytest.mark.asgi
    async def test_unknown_path_returns_404(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that unknown paths return HTTP 404."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/unknown")

        assert response.status_code == 404


class TestASGIJSONErrorResponses:
    """Tests for JSON-formatted error responses."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.MetricsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_metrics_endpoint_returns_json_error_on_failure(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /metrics returns JSON-formatted error on failure."""
        app = create_asgi_app(log_storage, metrics_storage)

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Encoding failed")

        async with mock_encoder("encode_ndjson", failing_encode):
            async with asgi_test_client(app) as client:
                response = await client.get("/metrics")

            assert response.status_code == 500
            assert response.headers["content-type"] == "application/json"
            data = response.json()
            assert data == {"error": "Internal Server Error"}

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointEncodingError")
    @pytest.mark.asgi
    async def test_logs_endpoint_returns_json_error_on_failure(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs returns JSON-formatted error on failure."""
        app = create_asgi_app(log_storage, metrics_storage)

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Encoding failed")

        async with mock_encoder("encode_logs", failing_encode):
            async with asgi_test_client(app) as client:
                response = await client.get("/logs")

            assert response.status_code == 500
            assert response.headers["content-type"] == "application/json"
            data = response.json()
            assert data == {"error": "Internal Server Error"}
