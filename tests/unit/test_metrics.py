"""Tests for metric helper functions."""

import time

import pytest

from observabilipy.core.metrics import counter, gauge, histogram, timer
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


class TestHistogram:
    """Tests for histogram() helper function."""

    @pytest.mark.core
    def test_histogram_returns_list_of_metric_samples(self) -> None:
        """Histogram returns a list of MetricSample instances."""
        samples = histogram("request_duration", value=0.25)
        assert isinstance(samples, list)
        assert all(isinstance(s, MetricSample) for s in samples)

    @pytest.mark.core
    def test_histogram_creates_bucket_samples(self) -> None:
        """Histogram creates bucket samples with _bucket suffix and le label."""
        samples = histogram("request_duration", value=0.25, buckets=[0.1, 0.5, 1.0])
        bucket_samples = [s for s in samples if "_bucket" in s.name]
        assert len(bucket_samples) == 4  # 3 buckets + +Inf
        assert all(s.name == "request_duration_bucket" for s in bucket_samples)
        assert all("le" in s.labels for s in bucket_samples)

    @pytest.mark.core
    def test_histogram_bucket_values_are_cumulative(self) -> None:
        """Histogram bucket values are cumulative counts."""
        samples = histogram("request_duration", value=0.25, buckets=[0.1, 0.5, 1.0])
        bucket_samples = [s for s in samples if "_bucket" in s.name]
        le_values = {s.labels["le"]: s.value for s in bucket_samples}

        # value=0.25 falls into le="0.5" bucket and above
        assert le_values["0.1"] == 0  # 0.25 > 0.1
        assert le_values["0.5"] == 1  # 0.25 <= 0.5
        assert le_values["1.0"] == 1  # 0.25 <= 1.0
        assert le_values["+Inf"] == 1  # always 1

    @pytest.mark.core
    def test_histogram_creates_sum_and_count_samples(self) -> None:
        """Histogram creates _sum and _count samples."""
        samples = histogram("request_duration", value=0.25, buckets=[0.1, 0.5, 1.0])
        names = [s.name for s in samples]
        assert "request_duration_sum" in names
        assert "request_duration_count" in names

        sum_sample = next(s for s in samples if s.name == "request_duration_sum")
        count_sample = next(s for s in samples if s.name == "request_duration_count")
        assert sum_sample.value == 0.25
        assert count_sample.value == 1

    @pytest.mark.core
    def test_histogram_propagates_labels(self) -> None:
        """Histogram propagates labels to all samples."""
        samples = histogram(
            "request_duration", value=0.25, labels={"method": "GET"}, buckets=[0.1]
        )
        for sample in samples:
            assert sample.labels.get("method") == "GET"

    @pytest.mark.core
    def test_histogram_uses_default_buckets(self) -> None:
        """Histogram uses default Prometheus buckets when none specified."""
        samples = histogram("request_duration", value=0.25)
        bucket_samples = [s for s in samples if "_bucket" in s.name]
        # Default: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10] + Inf
        assert len(bucket_samples) == 12

    @pytest.mark.core
    def test_histogram_all_samples_have_same_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All histogram samples have the same timestamp."""
        monkeypatch.setattr(time, "time", lambda: 1702300000.0)
        samples = histogram("request_duration", value=0.25)
        assert all(s.timestamp == 1702300000.0 for s in samples)


class TestPackageExports:
    """Tests for package-level exports."""

    @pytest.mark.core
    def test_helpers_importable_from_package(self) -> None:
        """Helper functions are importable from observabilipy package."""
        from observabilipy import counter, gauge

        assert callable(counter)
        assert callable(gauge)

    @pytest.mark.core
    def test_histogram_importable_from_package(self) -> None:
        """Histogram helper is importable from observabilipy package."""
        from observabilipy import histogram

        assert callable(histogram)

    @pytest.mark.core
    def test_default_histogram_buckets_importable_from_package(self) -> None:
        """DEFAULT_HISTOGRAM_BUCKETS is importable from observabilipy."""
        from observabilipy import DEFAULT_HISTOGRAM_BUCKETS

        assert isinstance(DEFAULT_HISTOGRAM_BUCKETS, list)
        assert len(DEFAULT_HISTOGRAM_BUCKETS) == 11  # Standard Prometheus buckets

    @pytest.mark.core
    def test_timer_importable_from_package(self) -> None:
        """Timer is importable from observabilipy package."""
        from observabilipy import timer

        assert callable(timer)

    @pytest.mark.core
    def test_timer_result_importable_from_package(self) -> None:
        """TimerResult is importable from observabilipy package."""
        from observabilipy import TimerResult

        assert TimerResult is not None


class TestTimer:
    """Tests for timer() context manager."""

    @pytest.mark.core
    def test_timer_returns_histogram_samples(self) -> None:
        """Timer context manager returns histogram samples."""
        with timer("request_duration") as t:
            pass
        assert isinstance(t.samples, list)
        assert len(t.samples) > 0

    @pytest.mark.core
    def test_timer_measures_elapsed_time(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Timer measures elapsed time during context."""
        call_count = 0

        def mock_perf_counter() -> float:
            nonlocal call_count
            call_count += 1
            return 100.0 if call_count == 1 else 100.5  # 0.5s elapsed

        monkeypatch.setattr(time, "perf_counter", mock_perf_counter)

        with timer("request_duration", buckets=[0.1, 1.0]) as t:
            pass

        sum_sample = next(s for s in t.samples if s.name == "request_duration_sum")
        assert sum_sample.value == 0.5

    @pytest.mark.core
    def test_timer_accepts_labels(self) -> None:
        """Timer propagates labels to histogram samples."""
        with timer("request_duration", labels={"method": "GET"}, buckets=[0.1]) as t:
            pass
        for sample in t.samples:
            assert sample.labels.get("method") == "GET"

    @pytest.mark.core
    def test_timer_accepts_custom_buckets(self) -> None:
        """Timer uses custom bucket boundaries."""
        with timer("request_duration", buckets=[0.1, 0.5]) as t:
            pass
        bucket_samples = [s for s in t.samples if "_bucket" in s.name]
        assert len(bucket_samples) == 3  # 2 buckets + +Inf

    @pytest.mark.core
    def test_timer_uses_default_buckets(self) -> None:
        """Timer uses default histogram buckets when none specified."""
        with timer("request_duration") as t:
            pass
        bucket_samples = [s for s in t.samples if "_bucket" in s.name]
        assert len(bucket_samples) == 12  # 11 default + +Inf

    @pytest.mark.core
    def test_timer_samples_have_same_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All timer samples have the same timestamp."""
        monkeypatch.setattr(time, "time", lambda: 1702300000.0)
        with timer("request_duration") as t:
            pass
        assert all(s.timestamp == 1702300000.0 for s in t.samples)
