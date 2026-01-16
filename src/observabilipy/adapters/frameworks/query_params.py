"""Shared query parameter parsing utilities for framework adapters.

This module provides utilities for parsing and validating query parameters
that are common across different framework adapters (ASGI, WSGI).
"""

# Valid log levels for validation
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _parse_since_param(params: dict[str, list[str]]) -> float:
    """Parse and validate the 'since' query parameter.

    Args:
        params: Parsed query string parameters (as returned by urllib.parse.parse_qs).

    Returns:
        Timestamp as float, defaulting to 0.0 if invalid or missing.
        Rejects negative, NaN, and infinite values, returning 0.0 for these cases.
    """
    # @tra: Adapter.ASGI.QueryParameter.InvalidUTF8
    # @tra: Adapter.ASGI.QueryParameter.SinceValidation
    try:
        value = float(params.get("since", ["0"])[0])
        # Reject negative, NaN, and infinite values
        if (
            value < 0
            or value != value
            or value == float("inf")
            or value == float("-inf")
        ):
            return 0.0
        return value
    except ValueError:
        return 0.0


def _parse_level_param(params: dict[str, list[str]]) -> str | None:
    """Parse and validate the 'level' query parameter.

    Args:
        params: Parsed query string parameters (as returned by urllib.parse.parse_qs).

    Returns:
        Validated level string (uppercase) or None if invalid/missing.
    """
    level_list = params.get("level", [None])
    level_raw = level_list[0] if level_list else None
    if level_raw and level_raw.upper() in VALID_LEVELS:
        return level_raw.upper()
    return None
