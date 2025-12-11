"""Example exposing container metrics from cgroups v2.

Reads CPU and memory metrics from /sys/fs/cgroup (cgroups v2) and exposes
them via Prometheus-style endpoints. Useful for containers that need to
report their own resource usage.

Run with:
    uvicorn examples.cgroups_example:app --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics

Note: Requires running inside a container or cgroups v2 enabled system.
Falls back to dummy values if cgroups are unavailable.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample

CGROUP_PATH = Path("/sys/fs/cgroup")

log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()


def read_cgroup_file(filename: str) -> str | None:
    """Read a cgroup file, return None if unavailable."""
    path = CGROUP_PATH / filename
    try:
        return path.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None


def get_cpu_usage_usec() -> int | None:
    """Get CPU usage in microseconds from cpu.stat."""
    content = read_cgroup_file("cpu.stat")
    if content is None:
        return None
    for line in content.splitlines():
        if line.startswith("usage_usec"):
            return int(line.split()[1])
    return None


def get_memory_bytes() -> int | None:
    """Get current memory usage in bytes."""
    content = read_cgroup_file("memory.current")
    if content is None:
        return None
    return int(content)


def get_memory_limit_bytes() -> int | None:
    """Get memory limit in bytes."""
    content = read_cgroup_file("memory.max")
    if content is None:
        return None
    if content == "max":
        return None  # No limit set
    return int(content)


class CpuTracker:
    """Track CPU percentage over time."""

    def __init__(self) -> None:
        self.last_usage_usec: int | None = None
        self.last_time: float | None = None

    def get_cpu_percent(self) -> float | None:
        """Calculate CPU percentage since last call."""
        current_usage = get_cpu_usage_usec()
        current_time = time.time()

        if current_usage is None:
            return None

        if self.last_usage_usec is None or self.last_time is None:
            self.last_usage_usec = current_usage
            self.last_time = current_time
            return 0.0

        usage_delta = current_usage - self.last_usage_usec
        time_delta = current_time - self.last_time

        self.last_usage_usec = current_usage
        self.last_time = current_time

        if time_delta <= 0:
            return 0.0

        # Convert microseconds to seconds, then to percentage
        cpu_percent = (usage_delta / 1_000_000) / time_delta * 100
        return cpu_percent


cpu_tracker = CpuTracker()


async def collect_container_metrics() -> None:
    """Collect container metrics every second."""
    cgroups_available = CGROUP_PATH.exists()

    msg = "cgroups v2 available" if cgroups_available else "cgroups v2 unavailable"
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO" if cgroups_available else "WARN",
            message=msg,
            attributes={"path": str(CGROUP_PATH)},
        )
    )

    while True:
        now = time.time()

        # CPU percentage
        cpu_percent = cpu_tracker.get_cpu_percent()
        if cpu_percent is not None:
            await metrics_storage.write(
                MetricSample(
                    name="container_cpu_percent",
                    timestamp=now,
                    value=cpu_percent,
                    labels={},
                )
            )

        # Memory usage
        memory_bytes = get_memory_bytes()
        if memory_bytes is not None:
            await metrics_storage.write(
                MetricSample(
                    name="container_memory_bytes",
                    timestamp=now,
                    value=float(memory_bytes),
                    labels={},
                )
            )

        # Memory limit
        memory_limit = get_memory_limit_bytes()
        if memory_limit is not None:
            await metrics_storage.write(
                MetricSample(
                    name="container_memory_limit_bytes",
                    timestamp=now,
                    value=float(memory_limit),
                    labels={},
                )
            )

            # Memory utilization percentage
            memory_percent = (memory_bytes / memory_limit) * 100 if memory_bytes else 0
            await metrics_storage.write(
                MetricSample(
                    name="container_memory_percent",
                    timestamp=now,
                    value=memory_percent,
                    labels={},
                )
            )

        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Start background metrics collection on startup."""
    asyncio.create_task(collect_container_metrics())
    yield


app = FastAPI(title="Container Metrics Example", lifespan=lifespan)
app.include_router(create_observability_router(log_storage, metrics_storage))
