"""Tests for the FastAPI example application endpoints."""

import pytest
from examples.fastapi_example import app
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.fastapi


@pytest.fixture
async def client() -> AsyncClient:
    """Create async test client for the example app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestMetricsEndpoint:
    """Tests for /metrics endpoint (NDJSON format)."""

    async def test_returns_ndjson_content_type(self, client: AsyncClient) -> None:
        """GET /metrics returns NDJSON content type."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

    async def test_accepts_since_parameter(self, client: AsyncClient) -> None:
        """GET /metrics?since= accepts timestamp parameter."""
        response = await client.get("/metrics?since=0")
        assert response.status_code == 200


class TestMetricsPrometheusEndpoint:
    """Tests for /metrics/prometheus endpoint."""

    async def test_returns_prometheus_content_type(self, client: AsyncClient) -> None:
        """GET /metrics/prometheus returns Prometheus text format."""
        response = await client.get("/metrics/prometheus")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "version=0.0.4" in response.headers["content-type"]


class TestLogsEndpoint:
    """Tests for /logs endpoint."""

    async def test_returns_ndjson_content_type(self, client: AsyncClient) -> None:
        """GET /logs returns NDJSON content type."""
        response = await client.get("/logs")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

    async def test_accepts_since_parameter(self, client: AsyncClient) -> None:
        """GET /logs?since= accepts timestamp parameter."""
        response = await client.get("/logs?since=0")
        assert response.status_code == 200

    async def test_accepts_level_parameter(self, client: AsyncClient) -> None:
        """GET /logs?level= accepts level filter parameter."""
        response = await client.get("/logs?level=INFO")
        assert response.status_code == 200


class TestDocstringDocumentation:
    """Tests that the example docstring documents all endpoints."""

    def test_documents_metrics_ndjson(self) -> None:
        """Docstring mentions /metrics returns NDJSON."""
        from examples import fastapi_example

        docstring = fastapi_example.__doc__ or ""
        assert "/metrics" in docstring
        assert "NDJSON" in docstring

    def test_documents_metrics_since_param(self) -> None:
        """Docstring mentions /metrics?since= parameter."""
        from examples import fastapi_example

        docstring = fastapi_example.__doc__ or ""
        assert "since" in docstring.lower()

    def test_documents_prometheus_endpoint(self) -> None:
        """Docstring mentions /metrics/prometheus endpoint."""
        from examples import fastapi_example

        docstring = fastapi_example.__doc__ or ""
        assert "/metrics/prometheus" in docstring

    def test_documents_logs_level_param(self) -> None:
        """Docstring mentions /logs?level= parameter."""
        from examples import fastapi_example

        docstring = fastapi_example.__doc__ or ""
        assert "level" in docstring.lower()
