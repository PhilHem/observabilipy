"""Observabilipy - Metrics and structured log collection for Python.

Quickstart
----------
1. Create storage (adapter layer - choose one):

    from observabilipy import InMemoryLogStorage, InMemoryMetricsStorage

    log_storage = InMemoryLogStorage()
    metrics_storage = InMemoryMetricsStorage()

2. Start the runtime (wires core to adapters):

    from observabilipy import EmbeddedRuntime

    runtime = EmbeddedRuntime(
        log_storage=log_storage,
        metrics_storage=metrics_storage,
    )
    await runtime.start()

3. Use the fluent API (core layer):

    from observabilipy import log, counter

    log("info", "User logged in", user_id=123)
    counter("logins_total", labels={"method": "oauth"})

4. Framework integration (optional - exposes /logs and /metrics endpoints):

    from observabilipy.adapters.frameworks.fastapi import create_observability_router

    app.include_router(create_observability_router(log_storage, metrics_storage))

For more examples, see the examples/ directory.
"""

from observabilipy.adapters.logging import ContextProvider, ObservabilipyHandler
from observabilipy.adapters.logging_context import (
    clear_log_context,
    get_log_context,
    log_context,
    set_log_context,
    update_log_context,
)
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
from observabilipy.core.instrument import InstrumentResult, instrument
from observabilipy.core.logs import (
    TimedLogResult,
    debug,
    error,
    info,
    log,
    log_exception,
    timed_log,
    warn,
)
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
    "log_exception",
    "timed_log",
    "TimedLogResult",
    "warn",
    # Metric helpers
    "counter",
    "DEFAULT_HISTOGRAM_BUCKETS",
    "gauge",
    "histogram",
    "timer",
    "TimerResult",
    # Instrumentation
    "instrument",
    "InstrumentResult",
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
    # Logging integration
    "ContextProvider",
    "ObservabilipyHandler",
    # Logging context helpers
    "clear_log_context",
    "get_log_context",
    "log_context",
    "set_log_context",
    "update_log_context",
    # Runtime
    "EmbeddedRuntime",
]
