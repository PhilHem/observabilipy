"""Core domain models for observability data."""

from dataclasses import dataclass, field

from observabilipy.core.exceptions import ConfigurationError


@dataclass(frozen=True)
class LogEntry:
    """A structured log entry.

    Attributes:
        timestamp: Unix timestamp in seconds.
        level: Log level (e.g., INFO, ERROR, DEBUG).
        message: The log message.
        attributes: Additional structured fields.

    Example:
        >>> entry = LogEntry(
        ...     timestamp=1702300000.0,
        ...     level="INFO",
        ...     message="User logged in",
        ...     attributes={"user_id": 123, "ip": "192.168.1.1"}
        ... )
        >>> entry.level
        'INFO'
        >>> entry.attributes["user_id"]
        123
    """

    timestamp: float
    level: str
    message: str
    attributes: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricSample:
    """A single metric measurement.

    Attributes:
        name: Metric name (e.g., http_requests_total).
        timestamp: Unix timestamp in seconds.
        value: The metric value.
        labels: Key-value pairs for metric dimensions.

    Example:
        >>> sample = MetricSample(
        ...     name="http_requests_total",
        ...     timestamp=1702300000.0,
        ...     value=42.0,
        ...     labels={"method": "GET", "status": "200"}
        ... )
        >>> sample.name
        'http_requests_total'
        >>> sample.labels["method"]
        'GET'
    """

    name: str
    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetentionPolicy:
    """Retention policy for log and metric data.

    Defines when data should be automatically cleaned up. Either or both
    constraints can be set. When both are set, data is deleted when either
    limit is exceeded.

    Attributes:
        max_age_seconds: Maximum age in seconds before deletion.
                        None means no age limit.
        max_count: Maximum number of entries to keep.
                  None means no count limit.

    Example:
        >>> # Age-based retention: delete after 1 hour
        >>> policy = RetentionPolicy(max_age_seconds=3600)
        >>> policy.max_age_seconds
        3600

        >>> # Count-based retention: keep last 1000 entries
        >>> policy = RetentionPolicy(max_count=1000)
        >>> policy.max_count
        1000
    """

    max_age_seconds: float | None = None
    max_count: int | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_age_seconds is not None and self.max_age_seconds <= 0:
            raise ConfigurationError(
                f"max_age_seconds must be positive, got {self.max_age_seconds}"
            )
        if self.max_count is not None and self.max_count <= 0:
            raise ConfigurationError(
                f"max_count must be positive, got {self.max_count}"
            )


@dataclass(frozen=True)
class LevelRetentionPolicy:
    """Per-level retention policy for log data.

    Allows different log levels to have different retention settings.
    For example, keep ERROR logs for 30 days but DEBUG logs for only 1 day.

    Attributes:
        policies: Mapping of log level (e.g., "ERROR", "INFO") to RetentionPolicy.
        default: Optional fallback policy for levels not in the policies mapping.

    Example:
        >>> policy = LevelRetentionPolicy(
        ...     policies={
        ...         "ERROR": RetentionPolicy(max_age_seconds=86400 * 30),  # 30 days
        ...         "DEBUG": RetentionPolicy(max_age_seconds=86400),       # 1 day
        ...     },
        ...     default=RetentionPolicy(max_age_seconds=86400 * 7),  # 7 days
        ... )
        >>> policy.get_policy_for_level("ERROR").max_age_seconds
        2592000
        >>> policy.get_policy_for_level("INFO").max_age_seconds  # Falls back to default
        604800
    """

    policies: dict[str, RetentionPolicy] = field(default_factory=dict)
    default: RetentionPolicy | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        for level_name in self.policies:
            if not level_name or not level_name.strip():
                raise ConfigurationError("level name cannot be empty")

    def get_policy_for_level(self, level: str) -> RetentionPolicy | None:
        """Get the retention policy for a specific log level.

        Args:
            level: The log level (e.g., "ERROR", "INFO", "DEBUG").

        Returns:
            The RetentionPolicy for this level, the default policy if no
            level-specific policy exists, or None if neither is defined.
        """
        return self.policies.get(level, self.default)
