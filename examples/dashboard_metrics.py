"""System metrics collection for the dashboard example."""

import asyncio
import time

from observabilipy import get_logger
from observabilipy.adapters.storage.in_memory import InMemoryMetricsStorage
from observabilipy.core.models import MetricSample

logger = get_logger(__name__)

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


async def collect_system_metrics(metrics_storage: InMemoryMetricsStorage) -> None:
    """Collect system CPU and memory metrics every second."""
    if psutil is None:
        return

    while True:
        now = time.time()

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        per_cpu = psutil.cpu_percent(interval=None, percpu=True)

        await metrics_storage.write(
            MetricSample(
                name="system_cpu_percent",
                timestamp=now,
                value=cpu_percent,
                labels={},
            )
        )

        # Per-CPU metrics
        for i, cpu_pct in enumerate(per_cpu):
            await metrics_storage.write(
                MetricSample(
                    name="system_cpu_percent_per_core",
                    timestamp=now,
                    value=cpu_pct,
                    labels={"core": str(i)},
                )
            )

        # Memory metrics
        mem = psutil.virtual_memory()
        await metrics_storage.write(
            MetricSample(
                name="system_memory_percent",
                timestamp=now,
                value=mem.percent,
                labels={},
            )
        )
        await metrics_storage.write(
            MetricSample(
                name="system_memory_used_bytes",
                timestamp=now,
                value=float(mem.used),
                labels={},
            )
        )
        await metrics_storage.write(
            MetricSample(
                name="system_memory_available_bytes",
                timestamp=now,
                value=float(mem.available),
                labels={},
            )
        )
        await metrics_storage.write(
            MetricSample(
                name="system_memory_total_bytes",
                timestamp=now,
                value=float(mem.total),
                labels={},
            )
        )

        # Swap metrics
        swap = psutil.swap_memory()
        await metrics_storage.write(
            MetricSample(
                name="system_swap_percent",
                timestamp=now,
                value=swap.percent,
                labels={},
            )
        )

        # Disk I/O (if available)
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                await metrics_storage.write(
                    MetricSample(
                        name="system_disk_read_bytes_total",
                        timestamp=now,
                        value=float(disk_io.read_bytes),
                        labels={},
                    )
                )
                await metrics_storage.write(
                    MetricSample(
                        name="system_disk_write_bytes_total",
                        timestamp=now,
                        value=float(disk_io.write_bytes),
                        labels={},
                    )
                )
        except Exception:  # noqa: S110
            pass

        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            await metrics_storage.write(
                MetricSample(
                    name="system_network_bytes_sent_total",
                    timestamp=now,
                    value=float(net_io.bytes_sent),
                    labels={},
                )
            )
            await metrics_storage.write(
                MetricSample(
                    name="system_network_bytes_recv_total",
                    timestamp=now,
                    value=float(net_io.bytes_recv),
                    labels={},
                )
            )
        except Exception as e:
            logger.with_fields(error=str(e)).debug("Metrics unavailable")

        await asyncio.sleep(1)
