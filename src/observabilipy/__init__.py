"""Observabilipy - Metrics and structured log collection for Python.

This module re-exports the most commonly used classes for convenient imports:

    from observabilipy import LogEntry, MetricSample, InMemoryLogStorage

For framework adapters, import from the submodules:

    from observabilipy.adapters.frameworks.fastapi import create_observability_router
    from observabilipy.adapters.frameworks.django import (
        create_observability_urlpatterns,
    )
"""

from observabilipy.adapters.storage import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
    RingBufferLogStorage,
    RingBufferMetricsStorage,
    SQLiteLogStorage,
    SQLiteMetricsStorage,
)
from observabilipy.core.encoding.ndjson import encode_ndjson
from observabilipy.core.exceptions import ConfigurationError, ObservabilityError
from observabilipy.core.logs import debug, error, info, log, warn
from observabilipy.core.metrics import (
    DEFAULT_HISTOGRAM_BUCKETS,
    TimerResult,
    counter,
    gauge,
    histogram,
    timer,
)
from observabilipy.core.models import (
    LevelRetentionPolicy,
    LogEntry,
    MetricSample,
    RetentionPolicy,
)
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort
from observabilipy.runtime import EmbeddedRuntime

__all__ = [
    # Models
    "LevelRetentionPolicy",
    "LogEntry",
    "MetricSample",
    "RetentionPolicy",
    # Log helpers
    "debug",
    "error",
    "info",
    "log",
    "warn",
    # Metric helpers
    "counter",
    "DEFAULT_HISTOGRAM_BUCKETS",
    "gauge",
    "histogram",
    "timer",
    "TimerResult",
    # Ports
    "LogStoragePort",
    "MetricsStoragePort",
    # Encoding
    "encode_ndjson",
    # Exceptions
    "ConfigurationError",
    "ObservabilityError",
    # Storage
    "InMemoryLogStorage",
    "InMemoryMetricsStorage",
    "RingBufferLogStorage",
    "RingBufferMetricsStorage",
    "SQLiteLogStorage",
    "SQLiteMetricsStorage",
    # Runtime
    "EmbeddedRuntime",
]
