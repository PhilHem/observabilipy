"""Integration tests for FastAPI adapter."""

import json
from typing import Annotated

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from observabilipy.adapters.frameworks.fastapi import (
    Instrumented,
    create_instrumented_dependency,
    create_observability_router,
)
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample


class TestFastAPIMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    @pytest.mark.fastapi
    async def test_metrics_endpoint_returns_ndjson(self) -> None:
        """Metrics endpoint returns data in NDJSON format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "path": "/api"},
            )
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["name"] == "http_requests_total"
        assert parsed["value"] == 42.0
        assert parsed["labels"] == {"method": "GET", "path": "/api"}

    @pytest.mark.fastapi
    async def test_metrics_endpoint_content_type(self) -> None:
        """Metrics endpoint returns correct content type for NDJSON."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]

    @pytest.mark.fastapi
    async def test_metrics_endpoint_empty_storage(self) -> None:
        """Metrics endpoint returns empty body when no metrics."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.fastapi
    async def test_metrics_endpoint_since_parameter(self) -> None:
        """Metrics endpoint filters by since parameter."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300000.0, value=1.0)
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300002.0, value=2.0)
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics", params={"since": 1702300001.0})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["value"] == 2.0


class TestFastAPIMetricsPrometheusEndpoint:
    """Tests for the /metrics/prometheus endpoint."""

    @pytest.mark.fastapi
    async def test_metrics_prometheus_endpoint_returns_prometheus_format(self) -> None:
        """Metrics prometheus endpoint returns data in Prometheus text format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await metrics_storage.write(
            MetricSample(
                name="http_requests_total",
                timestamp=1702300000.0,
                value=42.0,
                labels={"method": "GET", "path": "/api"},
            )
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert 'http_requests_total{method="GET",path="/api"} 42.0' in response.text

    @pytest.mark.fastapi
    async def test_metrics_prometheus_endpoint_content_type(self) -> None:
        """Metrics prometheus endpoint returns correct content type."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "version=0.0.4" in response.headers["content-type"]

    @pytest.mark.fastapi
    async def test_metrics_prometheus_endpoint_empty_storage(self) -> None:
        """Metrics prometheus endpoint returns empty body when no metrics."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.fastapi
    async def test_metrics_prometheus_uses_encode_current(self) -> None:
        """Metrics prometheus endpoint keeps only latest sample per metric."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300000.0, value=1.0, labels={})
        )
        await metrics_storage.write(
            MetricSample(name="counter", timestamp=1702300002.0, value=5.0, labels={})
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        lines = [line for line in response.text.strip().split("\n") if line]
        assert len(lines) == 1  # Only latest sample
        assert "5.0" in lines[0]


class TestFastAPILogsEndpoint:
    """Tests for the /logs endpoint."""

    @pytest.mark.fastapi
    async def test_logs_endpoint_returns_ndjson(self) -> None:
        """Logs endpoint returns data in NDJSON format."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(
                timestamp=1702300000.0,
                level="INFO",
                message="Application started",
            )
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs")

        assert response.status_code == 200
        parsed = json.loads(response.text.strip())
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Application started"

    @pytest.mark.fastapi
    async def test_logs_endpoint_content_type(self) -> None:
        """Logs endpoint returns correct content type for NDJSON."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs")

        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]

    @pytest.mark.fastapi
    async def test_logs_endpoint_empty_storage(self) -> None:
        """Logs endpoint returns empty body when no logs."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs")

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.fastapi
    async def test_logs_endpoint_since_parameter(self) -> None:
        """Logs endpoint filters by since parameter."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="INFO", message="Old log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="INFO", message="New log")
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs", params={"since": 1702300001.0})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["message"] == "New log"

    @pytest.mark.fastapi
    async def test_logs_endpoint_level_parameter(self) -> None:
        """Logs endpoint filters by level parameter."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="ERROR", message="Error log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300001.0, level="INFO", message="Info log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="DEBUG", message="Debug log")
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs", params={"level": "ERROR"})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error log"

    @pytest.mark.fastapi
    async def test_logs_endpoint_level_parameter_case_insensitive(self) -> None:
        """Logs endpoint level filter is case-insensitive."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="ERROR", message="Error log")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300001.0, level="INFO", message="Info log")
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs", params={"level": "error"})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["level"] == "ERROR"

    @pytest.mark.fastapi
    async def test_logs_endpoint_combines_since_and_level(self) -> None:
        """Logs endpoint combines since and level parameters."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="ERROR", message="Old error")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300002.0, level="ERROR", message="New error")
        )
        await log_storage.write(
            LogEntry(timestamp=1702300003.0, level="INFO", message="New info")
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs", params={"since": 1702300001.0, "level": "ERROR"})

        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["message"] == "New error"

    @pytest.mark.fastapi
    async def test_logs_endpoint_level_returns_empty_for_nonexistent(self) -> None:
        """Logs endpoint returns empty for non-existent level."""
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()
        await log_storage.write(
            LogEntry(timestamp=1702300000.0, level="INFO", message="Info log")
        )

        app = FastAPI()
        app.include_router(create_observability_router(log_storage, metrics_storage))
        client = TestClient(app)

        response = client.get("/logs", params={"level": "FATAL"})

        assert response.status_code == 200
        assert response.text == ""


class TestFastAPIInstrumentedDependency:
    """Tests for create_instrumented_dependency."""

    @pytest.mark.fastapi
    async def test_create_instrumented_dependency_returns_callable(self) -> None:
        """create_instrumented_dependency returns a callable."""
        storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(storage)
        assert callable(get_instrumented)

    @pytest.mark.fastapi
    async def test_instrumented_context_writes_metrics_to_storage(self) -> None:
        """Instrumented context manager writes metrics to storage."""
        storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(storage)

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(
            instr: Annotated[Instrumented, Depends(get_instrumented)],
        ) -> dict[str, str]:
            async with instr("test_operation"):
                return {"status": "ok"}

        client = TestClient(app)
        client.get("/test")

        count = await storage.count()
        assert count > 0  # Counter + histogram samples

    @pytest.mark.fastapi
    async def test_instrumented_writes_counter_sample(self) -> None:
        """Instrumented writes counter with _total suffix."""
        storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(storage)

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(
            instr: Annotated[Instrumented, Depends(get_instrumented)],
        ) -> dict[str, str]:
            async with instr("my_operation"):
                return {"status": "ok"}

        client = TestClient(app)
        client.get("/test")

        samples = [s async for s in storage.read()]
        counter_samples = [s for s in samples if s.name == "my_operation_total"]
        assert len(counter_samples) == 1

    @pytest.mark.fastapi
    async def test_instrumented_writes_histogram_samples(self) -> None:
        """Instrumented writes histogram duration samples."""
        storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(storage)

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(
            instr: Annotated[Instrumented, Depends(get_instrumented)],
        ) -> dict[str, str]:
            async with instr("my_operation"):
                return {"status": "ok"}

        client = TestClient(app)
        client.get("/test")

        samples = [s async for s in storage.read()]
        histogram_samples = [s for s in samples if "duration_seconds" in s.name]
        assert len(histogram_samples) > 0

    @pytest.mark.fastapi
    async def test_instrumented_accepts_custom_labels(self) -> None:
        """Instrumented accepts custom labels."""
        storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(storage)

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(
            instr: Annotated[Instrumented, Depends(get_instrumented)],
        ) -> dict[str, str]:
            async with instr("my_operation", labels={"source": "db"}):
                return {"status": "ok"}

        client = TestClient(app)
        client.get("/test")

        samples = [s async for s in storage.read()]
        counter = next(s for s in samples if s.name == "my_operation_total")
        assert counter.labels.get("source") == "db"

    @pytest.mark.fastapi
    async def test_instrumented_captures_exception(self) -> None:
        """Instrumented captures exceptions and sets error status."""
        storage = InMemoryMetricsStorage()
        get_instrumented = create_instrumented_dependency(storage)

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(
            instr: Annotated[Instrumented, Depends(get_instrumented)],
        ) -> dict[str, str]:
            async with instr("my_operation"):
                raise ValueError("test error")

        client = TestClient(app, raise_server_exceptions=False)
        client.get("/test")

        samples = [s async for s in storage.read()]
        counter = next(s for s in samples if s.name == "my_operation_total")
        assert counter.labels.get("status") == "error"
