"""Tests for retention logic functions."""

import pytest

from observability.core.models import RetentionPolicy
from observability.core.retention import calculate_age_threshold, should_delete_by_count


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
