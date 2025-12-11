"""Pure retention logic functions.

These functions calculate retention decisions without performing I/O.
Used by EmbeddedRuntime to determine what data to delete.
"""

from observabilipy.core.models import LevelRetentionPolicy, RetentionPolicy


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


def calculate_level_age_threshold(
    policy: LevelRetentionPolicy, level: str, current_time: float
) -> float | None:
    """Calculate timestamp threshold for level-based age retention.

    Args:
        policy: The per-level retention policy.
        level: The log level to calculate threshold for.
        current_time: Current Unix timestamp in seconds.

    Returns:
        Timestamp threshold for this level, or None if no age limit.
    """
    level_policy = policy.get_policy_for_level(level)
    if level_policy is None:
        return None
    return calculate_age_threshold(level_policy, current_time)


def should_delete_by_level_count(
    policy: LevelRetentionPolicy, level: str, current_count: int
) -> bool:
    """Check if count-based deletion is needed for a specific level.

    Args:
        policy: The per-level retention policy.
        level: The log level to check.
        current_count: Current number of entries for this level.

    Returns:
        True if current_count exceeds the level's max_count limit.
    """
    level_policy = policy.get_policy_for_level(level)
    if level_policy is None:
        return False
    return should_delete_by_count(level_policy, current_count)
