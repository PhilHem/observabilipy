"""Tests for ASGI query parameter parsing helpers.

This module tests the internal helper functions for parsing query parameters
from ASGI scope, including handling of invalid UTF-8 bytes.
"""

from __future__ import annotations

import pytest

from observabilipy.adapters.frameworks.asgi import (
    Scope,
    _parse_level_param,
    _parse_query_params,
    _parse_since_param,
)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.InvalidUTF8")
def test_parse_since_param_handles_invalid_utf8_bytes():
    """_parse_since_param should handle invalid UTF-8 bytes in query string."""

    # Arrange: Simulate invalid UTF-8 bytes in query string that would be
    # decoded with errors='replace' to produce placeholder characters
    query_string = "since=\ufffd\ufffd".encode()  # Replacement chars
    params = __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs(
        query_string.decode("utf-8", errors="replace")
    )

    # Act: Parse the 'since' parameter
    result = _parse_since_param(params)

    # Assert: Should return default value (0.0) without raising
    assert isinstance(result, float)
    assert result == 0.0


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.InvalidUTF8")
def test_parse_level_param_handles_invalid_utf8_bytes():
    """_parse_level_param should handle invalid UTF-8 bytes in query string."""

    # Arrange: Simulate invalid UTF-8 bytes in query string that would be
    # decoded with errors='replace' to produce placeholder characters
    query_string = "level=\ufffd\ufffd".encode()  # Replacement chars
    params = __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs(
        query_string.decode("utf-8", errors="replace")
    )

    # Act: Parse the 'level' parameter
    result = _parse_level_param(params)

    # Assert: Should return None without raising
    assert result is None


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.Parser")
def test_parse_query_params_extracts_all_params():
    """_parse_query_params should extract all parameters from scope query_string."""

    # Arrange: Create scope with query string
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"since=12345.0&level=INFO&other=value",
        "headers": [],
    }

    # Act: Parse query parameters
    result = _parse_query_params(scope)

    # Assert: Should return dict with all parameters
    assert result == {"since": ["12345.0"], "level": ["INFO"], "other": ["value"]}


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.Parser")
def test_parse_query_params_handles_missing_query_string():
    """_parse_query_params should handle scope without query_string key."""

    # Arrange: Create scope without query_string key
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }

    # Act: Parse query parameters
    result = _parse_query_params(scope)

    # Assert: Should return empty dict
    assert result == {}


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.SinceValidation")
def test_since_rejects_negative_timestamp():
    """_parse_since_param should reject negative timestamps and return 0.0."""

    # Arrange: Create params dict with negative since value
    params = {"since": ["-100.5"]}

    # Act: Parse the 'since' parameter
    result = _parse_since_param(params)

    # Assert: Should return default value (0.0)
    assert result == 0.0


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.SinceValidation")
def test_since_rejects_nan():
    """_parse_since_param should reject NaN values and return 0.0."""

    # Arrange: Create params dict with NaN since value
    params = {"since": ["nan"]}

    # Act: Parse the 'since' parameter
    result = _parse_since_param(params)

    # Assert: Should return default value (0.0)
    assert result == 0.0


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.SinceValidation")
def test_since_rejects_infinity():
    """_parse_since_param should reject infinity values and return 0.0."""

    # Arrange: Create params dict with infinity since value
    params = {"since": ["inf"]}

    # Act: Parse the 'since' parameter
    result = _parse_since_param(params)

    # Assert: Should return default value (0.0)
    assert result == 0.0


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.ASGI.QueryParameter.SinceValidation")
def test_since_accepts_valid_timestamp():
    """_parse_since_param should accept valid positive timestamps."""

    # Arrange: Create params dict with valid positive since value
    params = {"since": ["1234567890.123"]}

    # Act: Parse the 'since' parameter
    result = _parse_since_param(params)

    # Assert: Should return the parsed float value
    assert result == 1234567890.123
