"""Integration tests for dashboard NDJSON metrics fetching."""

import json

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from observabilipy.core.models import MetricSample

# Import the dashboard app directly to test its endpoints
dashboard_example = pytest.importorskip(
    "examples.dashboard_example",
    reason="dashboard example requires psutil",
)


class TestDashboardNDJSONIntegration:
    """Test that dashboard uses /metrics?since= for incremental updates."""

    @pytest.mark.fastapi
    def test_dashboard_no_custom_metrics_endpoint(self) -> None:
        """Dashboard should not have a custom /api/metrics endpoint.

        The dashboard should use the standard /metrics NDJSON endpoint
        instead of a custom JSON endpoint.
        """
        # The dashboard app should NOT have /api/metrics after refactoring
        routes = [route.path for route in dashboard_example.app.routes]
        assert "/api/metrics" not in routes, (
            "Dashboard should use /metrics NDJSON endpoint, not /api/metrics"
        )

    @pytest.mark.fastapi
    def test_metrics_endpoint_available(self) -> None:
        """Dashboard should expose /metrics endpoint from router."""
        routes = [route.path for route in dashboard_example.app.routes]
        assert "/metrics" in routes

    @pytest.mark.fastapi
    async def test_dashboard_metrics_ndjson_format(self) -> None:
        """Dashboard /metrics returns NDJSON that frontend can parse."""
        # Write a sample metric directly to the storage
        await dashboard_example.metrics_storage.write(
            MetricSample(
                name="test_metric",
                timestamp=1702300000.0,
                value=42.0,
                labels={"env": "test"},
            )
        )

        client = TestClient(dashboard_example.app)
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]

        # Parse as NDJSON (split on newlines, parse each line)
        lines = response.text.strip().split("\n")
        samples = [json.loads(line) for line in lines if line]

        # Find our test metric
        test_samples = [s for s in samples if s["name"] == "test_metric"]
        assert len(test_samples) >= 1
        assert test_samples[-1]["value"] == 42.0
        assert test_samples[-1]["labels"] == {"env": "test"}

    @pytest.mark.fastapi
    async def test_dashboard_metrics_since_filter(self) -> None:
        """Dashboard /metrics?since= returns only newer samples."""
        # Clear existing data and add samples at specific timestamps
        await dashboard_example.metrics_storage.write(
            MetricSample(
                name="incremental_test",
                timestamp=1000.0,
                value=1.0,
            )
        )
        await dashboard_example.metrics_storage.write(
            MetricSample(
                name="incremental_test",
                timestamp=2000.0,
                value=2.0,
            )
        )
        await dashboard_example.metrics_storage.write(
            MetricSample(
                name="incremental_test",
                timestamp=3000.0,
                value=3.0,
            )
        )

        client = TestClient(dashboard_example.app)

        # Fetch only samples after timestamp 1500
        response = client.get("/metrics", params={"since": 1500.0})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        samples = [json.loads(line) for line in lines if line]

        # Filter to our test metric
        test_samples = [s for s in samples if s["name"] == "incremental_test"]

        # Should only have samples with timestamp > 1500
        for sample in test_samples:
            assert sample["timestamp"] > 1500.0

    @pytest.mark.fastapi
    def test_dashboard_html_uses_metrics_endpoint(self) -> None:
        """Dashboard HTML should fetch from /metrics, not /api/metrics."""
        client = TestClient(dashboard_example.app)
        response = client.get("/")

        assert response.status_code == 200
        html = response.text

        # Should use /metrics endpoint with since parameter
        assert "/metrics?since=" in html or "'/metrics'" in html or '"/metrics"' in html

        # Should NOT reference the old /api/metrics endpoint in fetch calls
        # (It may still appear in links section, which is OK)
        # Check that the fetch() call doesn't use /api/metrics
        assert "fetch('/api/metrics')" not in html
        assert 'fetch("/api/metrics")' not in html

    @pytest.mark.fastapi
    def test_dashboard_html_has_ndjson_parser(self) -> None:
        """Dashboard HTML should include NDJSON parsing logic."""
        client = TestClient(dashboard_example.app)
        response = client.get("/")

        assert response.status_code == 200
        html = response.text

        # Should have NDJSON parsing (split on newlines, parse each line)
        assert "split" in html  # For splitting NDJSON lines
        assert "JSON.parse" in html  # For parsing each line
