"""Core domain models for observability data."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LogEntry:
    """A structured log entry.

    Attributes:
        timestamp: Unix timestamp in seconds.
        level: Log level (e.g., INFO, ERROR, DEBUG).
        message: The log message.
        attributes: Additional structured fields.
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
    """

    name: str
    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)
