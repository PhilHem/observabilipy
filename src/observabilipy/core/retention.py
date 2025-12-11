"""Pure retention logic functions.

These functions calculate retention decisions without performing I/O.
Used by EmbeddedRuntime to determine what data to delete.
"""

from observabilipy.core.models import RetentionPolicy


def calculate_age_threshold(
    policy: RetentionPolicy, current_time: float
) -> float | None:
    """Calculate timestamp threshold for age-based retention.

    Args:
        policy: The retention policy to apply.
        current_time: Current Unix timestamp in seconds.

    Returns:
        Timestamp threshold: entries with timestamp < this value should be deleted.
        None if no age limit is configured in the policy.
    """
    if policy.max_age_seconds is None:
        return None
    return current_time - policy.max_age_seconds


def should_delete_by_count(policy: RetentionPolicy, current_count: int) -> bool:
    """Check if count-based deletion is needed.

    Args:
        policy: The retention policy to apply.
        current_count: Current number of entries in storage.

    Returns:
        True if current_count exceeds the max_count limit, False otherwise.
        Always False if no count limit is configured.
    """
    if policy.max_count is None:
        return False
    return current_count > policy.max_count
