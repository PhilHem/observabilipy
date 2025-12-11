"""Tests for core models."""

import pytest

from observabilipy.core.exceptions import ConfigurationError
from observabilipy.core.models import (
    LevelRetentionPolicy,
    LogEntry,
    MetricSample,
    RetentionPolicy,
)


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

    @pytest.mark.core
    def test_retention_policy_rejects_negative_max_age(self) -> None:
        with pytest.raises(ConfigurationError) as exc_info:
            RetentionPolicy(max_age_seconds=-1.0)
        assert "max_age_seconds" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    @pytest.mark.core
    def test_retention_policy_rejects_zero_max_age(self) -> None:
        with pytest.raises(ConfigurationError):
            RetentionPolicy(max_age_seconds=0.0)

    @pytest.mark.core
    def test_retention_policy_rejects_negative_max_count(self) -> None:
        with pytest.raises(ConfigurationError) as exc_info:
            RetentionPolicy(max_count=-1)
        assert "max_count" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    @pytest.mark.core
    def test_retention_policy_rejects_zero_max_count(self) -> None:
        with pytest.raises(ConfigurationError):
            RetentionPolicy(max_count=0)


class TestLevelRetentionPolicy:
    """Tests for LevelRetentionPolicy model."""

    @pytest.mark.core
    def test_creates_with_single_level_policy(self) -> None:
        """Can create policy with single level configuration."""
        error_policy = RetentionPolicy(max_age_seconds=2592000.0)  # 30 days
        policy = LevelRetentionPolicy(policies={"ERROR": error_policy})

        assert policy.policies["ERROR"] == error_policy

    @pytest.mark.core
    def test_creates_with_multiple_level_policies(self) -> None:
        """Can create policy with multiple levels."""
        policy = LevelRetentionPolicy(
            policies={
                "ERROR": RetentionPolicy(max_age_seconds=2592000.0),
                "INFO": RetentionPolicy(max_age_seconds=604800.0),
                "DEBUG": RetentionPolicy(max_age_seconds=86400.0),
            }
        )

        assert len(policy.policies) == 3

    @pytest.mark.core
    def test_creates_with_default_policy(self) -> None:
        """Can create policy with default for unspecified levels."""
        default = RetentionPolicy(max_age_seconds=86400.0)
        policy = LevelRetentionPolicy(policies={}, default=default)

        assert policy.default == default

    @pytest.mark.core
    def test_get_policy_for_level_returns_specific_policy(self) -> None:
        """get_policy_for_level returns level-specific policy when defined."""
        error_policy = RetentionPolicy(max_age_seconds=2592000.0)
        policy = LevelRetentionPolicy(
            policies={"ERROR": error_policy},
            default=RetentionPolicy(max_age_seconds=86400.0),
        )

        assert policy.get_policy_for_level("ERROR") == error_policy

    @pytest.mark.core
    def test_get_policy_for_level_returns_default_for_undefined_level(self) -> None:
        """get_policy_for_level returns default when level not specified."""
        default = RetentionPolicy(max_age_seconds=86400.0)
        policy = LevelRetentionPolicy(policies={}, default=default)

        assert policy.get_policy_for_level("WARN") == default

    @pytest.mark.core
    def test_get_policy_for_level_returns_none_when_no_default(self) -> None:
        """get_policy_for_level returns None when no default and level undefined."""
        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_age_seconds=100.0)}
        )

        assert policy.get_policy_for_level("DEBUG") is None

    @pytest.mark.core
    def test_is_frozen_dataclass(self) -> None:
        """LevelRetentionPolicy is immutable."""
        policy = LevelRetentionPolicy(policies={})
        with pytest.raises(AttributeError):
            policy.policies = {}  # type: ignore[misc]

    @pytest.mark.core
    def test_rejects_empty_level_name(self) -> None:
        """Empty string level name raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            LevelRetentionPolicy(policies={"": RetentionPolicy(max_age_seconds=100.0)})
        assert "level name" in str(exc_info.value).lower()

    @pytest.mark.core
    def test_rejects_whitespace_only_level_name(self) -> None:
        """Whitespace-only level name raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            LevelRetentionPolicy(
                policies={"   ": RetentionPolicy(max_age_seconds=100.0)}
            )
        assert "level name" in str(exc_info.value).lower()
