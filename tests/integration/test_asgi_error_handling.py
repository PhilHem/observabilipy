"""Integration tests for ASGI error handling and routing."""

from collections.abc import AsyncGenerator

import pytest

from observabilipy.adapters.frameworks.asgi import create_asgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)


@pytest.fixture
async def log_storage() -> AsyncGenerator[InMemoryLogStorage]:
    """Fixture providing an empty log storage."""
    return InMemoryLogStorage()


@pytest.fixture
async def metrics_storage() -> AsyncGenerator[InMemoryMetricsStorage]:
    """Fixture providing an empty metrics storage."""
    return InMemoryMetricsStorage()


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

        # Mock the encode_ndjson to raise an exception
        import observabilipy.adapters.frameworks.asgi as asgi_module

        original_encode = asgi_module.encode_ndjson

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Encoding failed")

        asgi_module.encode_ndjson = failing_encode

        try:
            async with asgi_test_client(app) as client:
                response = await client.get("/metrics")

            assert response.status_code == 500
            assert "error" in response.text.lower()
        finally:
            asgi_module.encode_ndjson = original_encode

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

        # Mock the encode_logs to raise an exception
        import observabilipy.adapters.frameworks.asgi as asgi_module

        original_encode = asgi_module.encode_logs

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Encoding failed")

        asgi_module.encode_logs = failing_encode

        try:
            async with asgi_test_client(app) as client:
                response = await client.get("/logs")

            assert response.status_code == 500
            assert "error" in response.text.lower()
        finally:
            asgi_module.encode_logs = original_encode

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

        # Mock the encode_ndjson to raise an exception
        import observabilipy.adapters.frameworks.asgi as asgi_module

        original_encode = asgi_module.encode_ndjson

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Sensitive database connection error: db://prod")

        asgi_module.encode_ndjson = failing_encode

        try:
            async with asgi_test_client(app) as client:
                response = await client.get("/metrics")

            assert response.status_code == 500
            # Error details must not be exposed
            assert "Sensitive database connection error" not in response.text
            assert "db://prod" not in response.text
            # Should contain generic message
            assert "Internal Server Error" in response.text
        finally:
            asgi_module.encode_ndjson = original_encode

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

        # Mock the encode_logs to raise an exception
        import observabilipy.adapters.frameworks.asgi as asgi_module

        original_encode = asgi_module.encode_logs

        async def failing_encode(*_args, **_kwargs):
            raise ValueError("Sensitive API key: secret_xyz789")

        asgi_module.encode_logs = failing_encode

        try:
            async with asgi_test_client(app) as client:
                response = await client.get("/logs")

            assert response.status_code == 500
            # Error details must not be exposed
            assert "Sensitive API key" not in response.text
            assert "secret_xyz789" not in response.text
            # Should contain generic message
            assert "Internal Server Error" in response.text
        finally:
            asgi_module.encode_logs = original_encode


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
