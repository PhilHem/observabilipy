"""Tests for retention logic functions."""

import pytest

from observabilipy.core.models import LevelRetentionPolicy, RetentionPolicy
from observabilipy.core.retention import (
    calculate_age_threshold,
    calculate_level_age_threshold,
    should_delete_by_count,
    should_delete_by_level_count,
)


class TestCalculateAgeThreshold:
    """Tests for age-based retention threshold calculation."""

    @pytest.mark.core
    def test_returns_none_when_no_age_limit(self) -> None:
        policy = RetentionPolicy()
        result = calculate_age_threshold(policy, current_time=1000.0)
        assert result is None

    @pytest.mark.core
    def test_calculates_threshold_from_max_age(self) -> None:
        policy = RetentionPolicy(max_age_seconds=3600.0)
        result = calculate_age_threshold(policy, current_time=5000.0)
        assert result == 1400.0  # 5000 - 3600

    @pytest.mark.core
    def test_ignores_max_count(self) -> None:
        policy = RetentionPolicy(max_age_seconds=100.0, max_count=50)
        result = calculate_age_threshold(policy, current_time=500.0)
        assert result == 400.0  # Only uses max_age_seconds


class TestShouldDeleteByCount:
    """Tests for count-based retention check."""

    @pytest.mark.core
    def test_returns_false_when_no_count_limit(self) -> None:
        policy = RetentionPolicy()
        result = should_delete_by_count(policy, current_count=1000)
        assert result is False

    @pytest.mark.core
    def test_returns_false_when_under_limit(self) -> None:
        policy = RetentionPolicy(max_count=100)
        result = should_delete_by_count(policy, current_count=50)
        assert result is False

    @pytest.mark.core
    def test_returns_false_when_at_limit(self) -> None:
        policy = RetentionPolicy(max_count=100)
        result = should_delete_by_count(policy, current_count=100)
        assert result is False

    @pytest.mark.core
    def test_returns_true_when_over_limit(self) -> None:
        policy = RetentionPolicy(max_count=100)
        result = should_delete_by_count(policy, current_count=101)
        assert result is True

    @pytest.mark.core
    def test_ignores_max_age(self) -> None:
        policy = RetentionPolicy(max_age_seconds=3600.0, max_count=10)
        result = should_delete_by_count(policy, current_count=5)
        assert result is False


class TestCalculateLevelAgeThreshold:
    """Tests for per-level age threshold calculation."""

    @pytest.mark.core
    def test_returns_threshold_for_specific_level(self) -> None:
        """Returns correct threshold for a configured level."""
        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_age_seconds=3600.0)}
        )

        result = calculate_level_age_threshold(policy, "ERROR", current_time=5000.0)

        assert result == 1400.0  # 5000 - 3600

    @pytest.mark.core
    def test_returns_default_threshold_for_unconfigured_level(self) -> None:
        """Returns default threshold when level not in policies."""
        policy = LevelRetentionPolicy(
            policies={},
            default=RetentionPolicy(max_age_seconds=1000.0),
        )

        result = calculate_level_age_threshold(policy, "INFO", current_time=5000.0)

        assert result == 4000.0  # 5000 - 1000

    @pytest.mark.core
    def test_returns_none_when_no_policy_for_level(self) -> None:
        """Returns None when no policy exists for level and no default."""
        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_age_seconds=100.0)}
        )

        result = calculate_level_age_threshold(policy, "DEBUG", current_time=5000.0)

        assert result is None

    @pytest.mark.core
    def test_returns_none_when_level_policy_has_no_age_limit(self) -> None:
        """Returns None when level policy has no max_age_seconds."""
        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_count=100)}
        )

        result = calculate_level_age_threshold(policy, "ERROR", current_time=5000.0)

        assert result is None


class TestShouldDeleteByLevelCount:
    """Tests for per-level count-based retention check."""

    @pytest.mark.core
    def test_returns_true_when_level_over_limit(self) -> None:
        """Returns True when level count exceeds max_count."""
        policy = LevelRetentionPolicy(policies={"ERROR": RetentionPolicy(max_count=10)})

        result = should_delete_by_level_count(policy, "ERROR", current_count=15)

        assert result is True

    @pytest.mark.core
    def test_returns_false_when_level_under_limit(self) -> None:
        """Returns False when level count under max_count."""
        policy = LevelRetentionPolicy(policies={"ERROR": RetentionPolicy(max_count=10)})

        result = should_delete_by_level_count(policy, "ERROR", current_count=5)

        assert result is False

    @pytest.mark.core
    def test_returns_false_when_level_at_limit(self) -> None:
        """Returns False when level count exactly at max_count."""
        policy = LevelRetentionPolicy(policies={"ERROR": RetentionPolicy(max_count=10)})

        result = should_delete_by_level_count(policy, "ERROR", current_count=10)

        assert result is False

    @pytest.mark.core
    def test_returns_false_when_no_policy_for_level(self) -> None:
        """Returns False when no policy exists for level."""
        policy = LevelRetentionPolicy(policies={})

        result = should_delete_by_level_count(policy, "DEBUG", current_count=1000)

        assert result is False

    @pytest.mark.core
    def test_uses_default_policy_for_unconfigured_level(self) -> None:
        """Uses default policy when level not in policies."""
        policy = LevelRetentionPolicy(
            policies={},
            default=RetentionPolicy(max_count=5),
        )

        result = should_delete_by_level_count(policy, "INFO", current_count=10)

        assert result is True

    @pytest.mark.core
    def test_returns_false_when_level_policy_has_no_count_limit(self) -> None:
        """Returns False when level policy has no max_count."""
        policy = LevelRetentionPolicy(
            policies={"ERROR": RetentionPolicy(max_age_seconds=100.0)}
        )

        result = should_delete_by_level_count(policy, "ERROR", current_count=1000)

        assert result is False
