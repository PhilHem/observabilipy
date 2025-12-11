"""Tests for core models."""

import pytest

from observability.core.models import LogEntry, MetricSample, RetentionPolicy


class TestLogEntry:
    """Tests for LogEntry model."""

    @pytest.mark.core
    def test_create_log_entry_with_required_fields(self) -> None:
        entry = LogEntry(
            timestamp=1702300000.0,
            level="INFO",
            message="Application started",
        )
        assert entry.timestamp == 1702300000.0
        assert entry.level == "INFO"
        assert entry.message == "Application started"
        assert entry.attributes == {}

    @pytest.mark.core
    def test_create_log_entry_with_attributes(self) -> None:
        entry = LogEntry(
            timestamp=1702300000.0,
            level="ERROR",
            message="Connection failed",
            attributes={"host": "localhost", "port": 5432},
        )
        assert entry.attributes == {"host": "localhost", "port": 5432}

    @pytest.mark.core
    def test_log_entry_is_immutable(self) -> None:
        entry = LogEntry(
            timestamp=1702300000.0,
            level="INFO",
            message="Test",
        )
        with pytest.raises(AttributeError):
            entry.level = "ERROR"  # type: ignore[misc]


class TestMetricSample:
    """Tests for MetricSample model."""

    @pytest.mark.core
    def test_create_metric_sample_with_required_fields(self) -> None:
        sample = MetricSample(
            name="http_requests_total",
            timestamp=1702300000.0,
            value=42.0,
        )
        assert sample.name == "http_requests_total"
        assert sample.timestamp == 1702300000.0
        assert sample.value == 42.0
        assert sample.labels == {}

    @pytest.mark.core
    def test_create_metric_sample_with_labels(self) -> None:
        sample = MetricSample(
            name="http_requests_total",
            timestamp=1702300000.0,
            value=100.0,
            labels={"method": "GET", "status": "200"},
        )
        assert sample.labels == {"method": "GET", "status": "200"}

    @pytest.mark.core
    def test_metric_sample_is_immutable(self) -> None:
        sample = MetricSample(
            name="http_requests_total",
            timestamp=1702300000.0,
            value=42.0,
        )
        with pytest.raises(AttributeError):
            sample.value = 100.0  # type: ignore[misc]


class TestRetentionPolicy:
    """Tests for RetentionPolicy model."""

    @pytest.mark.core
    def test_create_retention_policy_with_max_age(self) -> None:
        policy = RetentionPolicy(max_age_seconds=3600.0)
        assert policy.max_age_seconds == 3600.0
        assert policy.max_count is None

    @pytest.mark.core
    def test_create_retention_policy_with_max_count(self) -> None:
        policy = RetentionPolicy(max_count=1000)
        assert policy.max_age_seconds is None
        assert policy.max_count == 1000

    @pytest.mark.core
    def test_create_retention_policy_with_both(self) -> None:
        policy = RetentionPolicy(max_age_seconds=86400.0, max_count=10000)
        assert policy.max_age_seconds == 86400.0
        assert policy.max_count == 10000

    @pytest.mark.core
    def test_retention_policy_defaults_to_no_limits(self) -> None:
        policy = RetentionPolicy()
        assert policy.max_age_seconds is None
        assert policy.max_count is None

    @pytest.mark.core
    def test_retention_policy_is_immutable(self) -> None:
        policy = RetentionPolicy(max_age_seconds=3600.0)
        with pytest.raises(AttributeError):
            policy.max_age_seconds = 7200.0  # type: ignore[misc]
