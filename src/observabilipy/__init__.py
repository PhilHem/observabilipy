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
from observabilipy.core.exceptions import ConfigurationError, ObservabilityError
from observabilipy.core.models import LogEntry, MetricSample, RetentionPolicy
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort
from observabilipy.runtime import EmbeddedRuntime

__all__ = [
    # Models
    "LogEntry",
    "MetricSample",
    "RetentionPolicy",
    # Ports
    "LogStoragePort",
    "MetricsStoragePort",
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
