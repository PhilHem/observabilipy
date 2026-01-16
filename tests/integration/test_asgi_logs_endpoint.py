"""Integration tests for ASGI /logs endpoint."""

from collections.abc import AsyncGenerator

import pytest

from observabilipy.adapters.frameworks.asgi import create_asgi_app
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry


@pytest.fixture
async def log_storage_with_data() -> AsyncGenerator[InMemoryLogStorage]:
    """Fixture providing a log storage with sample data."""
    storage = InMemoryLogStorage()
    await storage.write(
        LogEntry(
            timestamp=1000.0,
            level="INFO",
            message="Test message",
            attributes={"key": "value"},
        )
    )
    return storage


class TestASGILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_logs_endpoint_returns_200(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs returns HTTP 200."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs")

        assert response.status_code == 200

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointContentType")
    @pytest.mark.asgi
    async def test_logs_endpoint_has_ndjson_content_type(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs returns correct Content-Type header."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs")

        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointNDJSON")
    @pytest.mark.asgi
    async def test_logs_endpoint_returns_ndjson_format(
        self,
        log_storage_with_data: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs returns data in NDJSON format."""
        app = create_asgi_app(log_storage_with_data, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs")

        assert "Test message" in response.text
        assert "INFO" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_filters_by_since(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs?since=X filters entries by timestamp."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Old message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="INFO",
                message="New message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?since=150")

        assert "New message" in response.text
        assert "Old message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_filters_by_level(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs?level=X filters entries by level."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="ERROR",
                message="Error message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?level=ERROR")

        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_level_filter_is_case_insensitive(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs?level=X is case-insensitive."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="ERROR",
                message="Error message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?level=error")

        assert "Error message" in response.text
        assert "Info message" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_combines_since_and_level(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs combines since and level filters."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="ERROR",
                message="Old error",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="ERROR",
                message="New error",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=300.0,
                level="INFO",
                message="New info",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?since=150&level=ERROR")

        assert "New error" in response.text
        assert "Old error" not in response.text
        assert "New info" not in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_level_returns_empty_for_nonexistent(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs treats invalid level as None (shows all)."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?level=FATAL")

        assert response.status_code == 200
        assert "Info message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointSinceFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_handles_invalid_since_param(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs handles invalid since param gracefully."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Test message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?since=invalid")

        assert response.status_code == 200
        assert "Test message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointLevelFilter")
    @pytest.mark.asgi
    async def test_logs_endpoint_validates_level_whitelist(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs validates level parameter against whitelist."""
        await log_storage.write(
            LogEntry(
                timestamp=100.0,
                level="INFO",
                message="Info message",
                attributes={},
            )
        )
        await log_storage.write(
            LogEntry(
                timestamp=200.0,
                level="ERROR",
                message="Error message",
                attributes={},
            )
        )
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs?level=INVALID_LEVEL")

        assert response.status_code == 200
        assert "Info message" in response.text
        assert "Error message" in response.text

    @pytest.mark.tier(2)
    @pytest.mark.tra("Adapter.ASGI.LogsEndpointHTTPStatus")
    @pytest.mark.asgi
    async def test_logs_empty_storage_returns_empty_body(
        self,
        log_storage: InMemoryLogStorage,
        metrics_storage: InMemoryMetricsStorage,
        asgi_test_client,
    ) -> None:
        """Test that /logs returns empty body when storage is empty."""
        app = create_asgi_app(log_storage, metrics_storage)

        async with asgi_test_client(app) as client:
            response = await client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""
