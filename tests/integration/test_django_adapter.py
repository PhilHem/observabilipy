"""Integration tests for Django adapter."""

import json
import sys

import pytest

django = pytest.importorskip("django", reason="django not installed")
from django.conf import settings
from django.test import AsyncClient

from observabilipy.adapters.frameworks.django import (
    create_observability_urlpatterns,
    instrument_view,
)
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        ROOT_URLCONF=__name__,
        DATABASES={},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()


# Module-level storage instances that fixtures will reset
_log_storage: InMemoryLogStorage = InMemoryLogStorage()
_metrics_storage: InMemoryMetricsStorage = InMemoryMetricsStorage()

# Initial URL patterns
urlpatterns = create_observability_urlpatterns(_log_storage, _metrics_storage)


@pytest.fixture(autouse=True)
def reset_storage() -> None:
    """Reset storage instances before each test."""
    global _log_storage, _metrics_storage, urlpatterns
    _log_storage = InMemoryLogStorage()
    _metrics_storage = InMemoryMetricsStorage()
    # Update urlpatterns to use fresh storage
    new_patterns = create_observability_urlpatterns(_log_storage, _metrics_storage)
    # Update module-level urlpatterns via sys.modules
    current_module = sys.modules[__name__]
    current_module.urlpatterns = new_patterns  # type: ignore[attr-defined]
    # Clear Django's URL cache to pick up new patterns
    from django.urls import clear_url_caches

    clear_url_caches()


@pytest.fixture
def log_storage() -> InMemoryLogStorage:
    """Provide the current log storage instance."""
    return _log_storage


@pytest.fixture
def metrics_storage() -> InMemoryMetricsStorage:
    """Provide the current metrics storage instance."""
    return _metrics_storage


class TestDjangoMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.django
    async def test_metrics_endpoint_returns_ndjson(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint returns data in NDJSON format."""
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "path": "/api"},
            )
        )

        client = AsyncClient()
        response = await client.get("/metrics")

        assert response.status_code == 200
        parsed = json.loads(response.content.decode().strip())
        assert parsed["name"] == "http_requests_total"
        assert parsed["value"] == 42.0
        assert parsed["labels"] == {"method": "GET", "path": "/api"}

    @pytest.mark.django
    async def test_metrics_endpoint_content_type(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint returns correct content type for NDJSON."""
        client = AsyncClient()
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "application/x-ndjson" in response["Content-Type"]

    @pytest.mark.django
    async def test_metrics_endpoint_empty_storage(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint returns empty body when no metrics."""
        client = AsyncClient()
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert response.content.decode() == ""

    @pytest.mark.django
    async def test_metrics_endpoint_since_parameter(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics endpoint filters by since parameter."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300000.0, value=1.0)
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300002.0, value=2.0)
        )

        client = AsyncClient()
        response = await client.get("/metrics", {"since": "1702300001.0"})

        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["value"] == 2.0


class TestDjangoMetricsPrometheusEndpoint:
    """Tests for the /metrics/prometheus endpoint."""

    @pytest.mark.django
    async def test_metrics_prometheus_endpoint_returns_prometheus_format(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics prometheus endpoint returns data in Prometheus text format."""
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "path": "/api"},
            )
        )

        client = AsyncClient()
        response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert (
            'http_requests_total{method="GET",path="/api"} 42.0'
            in response.content.decode()
        )

    @pytest.mark.django
    async def test_metrics_prometheus_endpoint_content_type(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics prometheus endpoint returns correct content type."""
        client = AsyncClient()
        response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert "text/plain" in response["Content-Type"]
        assert "version=0.0.4" in response["Content-Type"]

    @pytest.mark.django
    async def test_metrics_prometheus_endpoint_empty_storage(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics prometheus endpoint returns empty body when no metrics."""
        client = AsyncClient()
        response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.content.decode() == ""

    @pytest.mark.django
    async def test_metrics_prometheus_uses_encode_current(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """Metrics prometheus endpoint keeps only latest sample per metric."""
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300000.0, value=1.0, labels={})
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300002.0, value=5.0, labels={})
        )

        client = AsyncClient()
        response = await client.get("/metrics/prometheus")

        assert response.status_code == 200
        lines = [line for line in response.content.decode().strip().split("\n") if line]
        assert len(lines) == 1  # Only latest sample
        assert "5.0" in lines[0]


class TestDjangoLogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.django
    async def test_logs_endpoint_returns_ndjson(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns data in NDJSON format."""
        await log_storage.write(
            LogEntry(
                timestamp=1702300000.0,
                level="INFO",
                message="Application started",
            )
        )

        client = AsyncClient()
        response = await client.get("/logs")

        assert response.status_code == 200
        parsed = json.loads(response.content.decode().strip())
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Application started"

    @pytest.mark.django
    async def test_logs_endpoint_content_type(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns correct content type for NDJSON."""
        client = AsyncClient()
        response = await client.get("/logs")

        assert response.status_code == 200
        assert "application/x-ndjson" in response["Content-Type"]

    @pytest.mark.django
    async def test_logs_endpoint_empty_storage(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns empty body when no logs."""
        client = AsyncClient()
        response = await client.get("/logs")

        assert response.status_code == 200
        assert response.content.decode() == ""

    @pytest.mark.django
    async def test_logs_endpoint_since_parameter(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint filters by since parameter."""
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="INFO", message="Old log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="INFO", message="New log")
        )

        client = AsyncClient()
        response = await client.get("/logs", {"since": "1702300001.0"})

        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["message"] == "New log"

    @pytest.mark.django
    async def test_logs_endpoint_level_parameter(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint filters by level parameter."""
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="ERROR", message="Error log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300001.0, level="INFO", message="Info log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="DEBUG", message="Debug log")
        )

        client = AsyncClient()
        response = await client.get("/logs", {"level": "ERROR"})

        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error log"

    @pytest.mark.django
    async def test_logs_endpoint_level_parameter_case_insensitive(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint level filter is case-insensitive."""
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="ERROR", message="Error log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300001.0, level="INFO", message="Info log")
        )

        client = AsyncClient()
        response = await client.get("/logs", {"level": "error"})

        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["level"] == "ERROR"

    @pytest.mark.django
    async def test_logs_endpoint_combines_since_and_level(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint combines since and level parameters."""
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="ERROR", message="Old error")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="ERROR", message="New error")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300003.0, level="INFO", message="New info")
        )

        client = AsyncClient()
        response = await client.get(
            "/logs", {"since": "1702300001.0", "level": "ERROR"}
        )

        assert response.status_code == 200
        lines = response.content.decode().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["message"] == "New error"

    @pytest.mark.django
    async def test_logs_endpoint_level_returns_empty_for_nonexistent(
        self, log_storage: InMemoryLogStorage
    ) -> None:
        """Logs endpoint returns empty for non-existent level."""
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="INFO", message="Info log")
        )

        client = AsyncClient()
        response = await client.get("/logs", {"level": "FATAL"})

        assert response.status_code == 200
        assert response.content.decode() == ""


class TestDjangoInstrumentView:
    """Tests for instrument_view decorator."""

    @pytest.mark.django
    async def test_instrument_view_writes_metrics(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view writes metrics to storage."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage, name="test_view")
        async def my_view(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        request = HttpRequest()
        request.method = "GET"
        request.path = "/test"

        await my_view(request)

        count = await metrics_storage.count()
        assert count > 0

    @pytest.mark.django
    async def test_instrument_view_writes_counter(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view writes counter with _total suffix."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage, name="my_view")
        async def my_view(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        request = HttpRequest()
        request.method = "GET"
        request.path = "/test"

        await my_view(request)

        samples = [s async for s in metrics_storage.read()]
        counter_samples = [s for s in samples if s.name == "my_view_total"]
        assert len(counter_samples) == 1

    @pytest.mark.django
    async def test_instrument_view_writes_histogram(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view writes histogram duration samples."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage, name="my_view")
        async def my_view(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        request = HttpRequest()
        request.method = "GET"
        request.path = "/test"

        await my_view(request)

        samples = [s async for s in metrics_storage.read()]
        histogram_samples = [s for s in samples if "duration_seconds" in s.name]
        assert len(histogram_samples) > 0

    @pytest.mark.django
    async def test_instrument_view_uses_function_name_as_default(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view uses function name as default metric name."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage)
        async def user_list(request: HttpRequest) -> HttpResponse:
            return HttpResponse("[]")

        request = HttpRequest()
        request.method = "GET"
        request.path = "/users"

        await user_list(request)

        samples = [s async for s in metrics_storage.read()]
        counter = next(s for s in samples if "_total" in s.name)
        assert counter.name == "user_list_total"

    @pytest.mark.django
    async def test_instrument_view_adds_method_label(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view adds HTTP method as label."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage, name="my_view")
        async def my_view(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        request = HttpRequest()
        request.method = "POST"
        request.path = "/items"

        await my_view(request)

        samples = [s async for s in metrics_storage.read()]
        counter = next(s for s in samples if s.name == "my_view_total")
        assert counter.labels.get("method") == "POST"

    @pytest.mark.django
    async def test_instrument_view_accepts_custom_labels(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view accepts custom labels."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage, name="my_view", labels={"env": "prod"})
        async def my_view(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        request = HttpRequest()
        request.method = "GET"
        request.path = "/test"

        await my_view(request)

        samples = [s async for s in metrics_storage.read()]
        counter = next(s for s in samples if s.name == "my_view_total")
        assert counter.labels.get("env") == "prod"

    @pytest.mark.django
    async def test_instrument_view_captures_exception(
        self, metrics_storage: InMemoryMetricsStorage
    ) -> None:
        """instrument_view captures exceptions and sets error status."""
        from django.http import HttpRequest, HttpResponse

        @instrument_view(metrics_storage, name="my_view")
        async def my_view(request: HttpRequest) -> HttpResponse:
            raise ValueError("test error")

        request = HttpRequest()
        request.method = "GET"
        request.path = "/test"

        with pytest.raises(ValueError):
            await my_view(request)

        samples = [s async for s in metrics_storage.read()]
        counter = next(s for s in samples if s.name == "my_view_total")
        assert counter.labels.get("status") == "error"
