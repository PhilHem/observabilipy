"""Tests for metric helper functions."""

import time

import pytest

from observabilipy.core.metrics import counter, gauge
from observabilipy.core.models import MetricSample


class TestCounter:
    """Tests for counter() helper function."""

    @pytest.mark.core
    def test_counter_creates_metric_sample_with_name(self) -> None:
        """Counter creates a MetricSample with the given name."""
        sample = counter("requests_total")
        assert sample.name == "requests_total"

    @pytest.mark.core
    def test_counter_returns_metric_sample_type(self) -> None:
        """Counter returns a MetricSample instance."""
        sample = counter("requests_total")
        assert isinstance(sample, MetricSample)

    @pytest.mark.core
    def test_counter_auto_captures_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Counter automatically captures current timestamp."""
        monkeypatch.setattr(time, "time", lambda: 1702300000.0)
        sample = counter("requests_total")
        assert sample.timestamp == 1702300000.0

    @pytest.mark.core
    def test_counter_defaults_to_value_one(self) -> None:
        """Counter defaults to incrementing by 1."""
        sample = counter("requests_total")
        assert sample.value == 1.0

    @pytest.mark.core
    def test_counter_accepts_custom_value(self) -> None:
        """Counter accepts a custom increment value."""
        sample = counter("requests_total", value=5.0)
        assert sample.value == 5.0

    @pytest.mark.core
    def test_counter_accepts_labels(self) -> None:
        """Counter accepts dimension labels."""
        sample = counter("requests_total", labels={"method": "GET"})
        assert sample.labels == {"method": "GET"}

    @pytest.mark.core
    def test_counter_defaults_to_empty_labels(self) -> None:
        """Counter defaults to empty labels dict."""
        sample = counter("requests_total")
        assert sample.labels == {}

    @pytest.mark.core
    def test_counter_with_value_and_labels(self) -> None:
        """Counter accepts both custom value and labels."""
        sample = counter(
            "requests_total", value=3.0, labels={"method": "POST", "status": "200"}
        )
        assert sample.value == 3.0
        assert sample.labels == {"method": "POST", "status": "200"}


class TestGauge:
    """Tests for gauge() helper function."""

    @pytest.mark.core
    def test_gauge_creates_metric_sample(self) -> None:
        """Gauge creates a MetricSample with name and value."""
        sample = gauge("cpu_percent", 45.2)
        assert sample.name == "cpu_percent"
        assert sample.value == 45.2

    @pytest.mark.core
    def test_gauge_returns_metric_sample_type(self) -> None:
        """Gauge returns a MetricSample instance."""
        sample = gauge("cpu_percent", 45.2)
        assert isinstance(sample, MetricSample)

    @pytest.mark.core
    def test_gauge_auto_captures_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gauge automatically captures current timestamp."""
        monkeypatch.setattr(time, "time", lambda: 1702300000.0)
        sample = gauge("cpu_percent", 45.2)
        assert sample.timestamp == 1702300000.0

    @pytest.mark.core
    def test_gauge_accepts_labels(self) -> None:
        """Gauge accepts dimension labels."""
        sample = gauge("cpu_percent", 45.2, labels={"host": "server1"})
        assert sample.labels == {"host": "server1"}

    @pytest.mark.core
    def test_gauge_defaults_to_empty_labels(self) -> None:
        """Gauge defaults to empty labels dict."""
        sample = gauge("cpu_percent", 45.2)
        assert sample.labels == {}

    @pytest.mark.core
    def test_gauge_with_negative_value(self) -> None:
        """Gauge accepts negative values."""
        sample = gauge("temperature_celsius", -10.5)
        assert sample.value == -10.5

    @pytest.mark.core
    def test_gauge_with_zero_value(self) -> None:
        """Gauge accepts zero value."""
        sample = gauge("active_connections", 0.0)
        assert sample.value == 0.0


class TestPackageExports:
    """Tests for package-level exports."""

    @pytest.mark.core
    def test_helpers_importable_from_package(self) -> None:
        """Helper functions are importable from observabilipy package."""
        from observabilipy import counter, gauge

        assert callable(counter)
        assert callable(gauge)
