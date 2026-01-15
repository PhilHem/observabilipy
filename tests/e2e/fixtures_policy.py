"""Retention policy fixtures for E2E tests."""

import pytest

from observabilipy.core.models import RetentionPolicy


@pytest.fixture
def retention_policy_short() -> RetentionPolicy:
    """Retention policy for testing (very short for fast tests)."""
    return RetentionPolicy(max_age_seconds=0.1)


@pytest.fixture
def retention_policy_count() -> RetentionPolicy:
    """Retention policy based on count."""
    return RetentionPolicy(max_count=3)
