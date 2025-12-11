"""System metrics dashboard with Chart.js visualization.

Captures real system CPU and memory metrics using psutil and displays them
in an interactive HTML dashboard with live-updating charts.

Requirements:
    pip install psutil
    # or: uv add psutil

Run with:
    uvicorn examples.dashboard_example:app --reload

Then visit:
    http://localhost:8000/ - Interactive dashboard with live charts
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/api/metrics - JSON API for dashboard
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.models import LogEntry, MetricSample, RetentionPolicy
from observabilipy.runtime.embedded import EmbeddedRuntime

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]
    print("Warning: psutil not installed. Install with: pip install psutil")

# Storage (in-memory for this example, use SQLite for persistence)
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Retention: keep 10 minutes of data, max 1000 samples
log_retention = RetentionPolicy(max_age_seconds=600, max_count=1000)
metrics_retention = RetentionPolicy(max_age_seconds=600, max_count=5000)

# Runtime handles background cleanup
runtime = EmbeddedRuntime(
    log_storage=log_storage,
    log_retention=log_retention,
    metrics_storage=metrics_storage,
    metrics_retention=metrics_retention,
    cleanup_interval_seconds=30,
)


async def collect_system_metrics() -> None:
    """Collect system CPU and memory metrics every second."""
    if psutil is None:
        await log_storage.write(
            LogEntry(
                timestamp=time.time(),
                level="ERROR",
                message="psutil not installed - cannot collect system metrics",
                attributes={},
            )
        )
        return

    while True:
        now = time.time()

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count()
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
        except Exception:
            pass  # Disk I/O not available on all systems

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
        except Exception:
            pass

        # Log collection event periodically
        await log_storage.write(
            LogEntry(
                timestamp=now,
                level="DEBUG",
                message=f"Collected metrics: CPU={cpu_percent}%, Memory={mem.percent}%",
                attributes={"cpu_count": str(cpu_count)},
            )
        )

        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Start runtime and metrics collection on startup."""
    await runtime.start()
    asyncio.create_task(collect_system_metrics())
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Dashboard started - collecting system metrics",
            attributes={"retention_seconds": "600"},
        )
    )
    yield
    await runtime.stop()


app = FastAPI(title="System Metrics Dashboard", lifespan=lifespan)
app.include_router(create_observability_router(log_storage, metrics_storage))


@app.get("/api/metrics")
async def get_metrics_json() -> JSONResponse:
    """Return metrics as JSON for the dashboard."""
    metrics: dict[str, list[dict]] = {}

    async for sample in metrics_storage.scrape():
        key = sample.name
        if sample.labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(sample.labels.items()))
            key = f"{sample.name}{{{label_str}}}"

        if key not in metrics:
            metrics[key] = []
        metrics[key].append(
            {
                "timestamp": sample.timestamp,
                "value": sample.value,
            }
        )

    # Sort by timestamp
    for key in metrics:
        metrics[key].sort(key=lambda x: x["timestamp"])

    return JSONResponse(content=metrics)


@app.get("/api/logs")
async def get_logs_json() -> JSONResponse:
    """Return logs as JSON for the dashboard."""
    logs: list[dict] = []

    async for entry in log_storage.read():
        logs.append(
            {
                "timestamp": entry.timestamp,
                "level": entry.level,
                "message": entry.message,
                "attributes": entry.attributes,
            }
        )

    # Sort by timestamp descending (newest first)
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    # Return last 100 logs
    return JSONResponse(content=logs[:100])


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin-bottom: 10px;
            color: #00d9ff;
        }
        .status {
            text-align: center;
            margin-bottom: 20px;
            color: #888;
            font-size: 14px;
        }
        .status .live {
            color: #00ff88;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .card h2 {
            font-size: 16px;
            color: #00d9ff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card h2 .value {
            margin-left: auto;
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }
        .chart-container {
            position: relative;
            height: 200px;
        }
        .links {
            text-align: center;
            margin-top: 20px;
            padding: 15px;
            background: #16213e;
            border-radius: 8px;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        .links a {
            color: #00d9ff;
            margin: 0 15px;
            text-decoration: none;
        }
        .links a:hover {
            text-decoration: underline;
        }
        .logs-card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            max-width: 1600px;
            margin: 20px auto 0;
        }
        .logs-card h2 {
            font-size: 16px;
            color: #00d9ff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .logs-card h2 .count {
            margin-left: auto;
            font-size: 14px;
            color: #888;
        }
        .logs-container {
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
        }
        .log-entry {
            padding: 6px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        .log-entry:hover {
            background: rgba(255,255,255,0.03);
        }
        .log-time {
            color: #666;
            white-space: nowrap;
            min-width: 80px;
        }
        .log-level {
            font-weight: bold;
            min-width: 50px;
            text-align: center;
            padding: 1px 6px;
            border-radius: 3px;
        }
        .log-level.DEBUG { color: #888; background: rgba(136,136,136,0.2); }
        .log-level.INFO { color: #00d9ff; background: rgba(0,217,255,0.2); }
        .log-level.WARN { color: #ffd93d; background: rgba(255,217,61,0.2); }
        .log-level.ERROR { color: #ff6b6b; background: rgba(255,107,107,0.2); }
        .log-message {
            color: #ddd;
            flex: 1;
        }
        .log-attrs {
            color: #666;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <h1>System Metrics Dashboard</h1>
    <div class="status">
        <span class="live">●</span> Live - Updating every 2 seconds
    </div>

    <div class="dashboard">
        <div class="card">
            <h2>CPU Usage <span class="value" id="cpu-value">--%</span></h2>
            <div class="chart-container">
                <canvas id="cpuChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>Memory Usage <span class="value" id="mem-value">--%</span></h2>
            <div class="chart-container">
                <canvas id="memChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>Network I/O <span class="value" id="net-value">-- MB/s</span></h2>
            <div class="chart-container">
                <canvas id="netChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>Disk I/O <span class="value" id="disk-value">-- MB/s</span></h2>
            <div class="chart-container">
                <canvas id="diskChart"></canvas>
            </div>
        </div>
    </div>

    <div class="logs-card">
        <h2>Logs <span class="count" id="log-count">0 entries</span></h2>
        <div class="logs-container" id="logs-container">
            <div class="log-entry"><span class="log-message">Loading logs...</span></div>
        </div>
    </div>

    <div class="links">
        <a href="/metrics" target="_blank">Prometheus Metrics</a>
        <a href="/logs" target="_blank">NDJSON Logs</a>
        <a href="/api/metrics" target="_blank">JSON API</a>
    </div>

    <script>
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'second',
                        displayFormats: { second: 'HH:mm:ss' }
                    },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#888', maxTicksLimit: 6 }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#888' }
                }
            }
        };

        function createChart(ctx, label, color, yMax = null) {
            const opts = JSON.parse(JSON.stringify(chartOptions));
            if (yMax) opts.scales.y.max = yMax;
            return new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: label,
                        data: [],
                        borderColor: color,
                        backgroundColor: color + '20',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0
                    }]
                },
                options: opts
            });
        }

        const cpuChart = createChart(document.getElementById('cpuChart'), 'CPU %', '#00d9ff', 100);
        const memChart = createChart(document.getElementById('memChart'), 'Memory %', '#ff6b6b', 100);
        const netChart = createChart(document.getElementById('netChart'), 'Network', '#00ff88');
        const diskChart = createChart(document.getElementById('diskChart'), 'Disk', '#ffd93d');

        // Track previous values for rate calculation
        let prevNetSent = null, prevNetRecv = null, prevNetTime = null;
        let prevDiskRead = null, prevDiskWrite = null, prevDiskTime = null;

        async function updateCharts() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                // CPU
                if (data['system_cpu_percent']) {
                    const cpuData = data['system_cpu_percent'].map(d => ({
                        x: d.timestamp * 1000,
                        y: d.value
                    }));
                    cpuChart.data.datasets[0].data = cpuData;
                    cpuChart.update('none');
                    const latest = cpuData[cpuData.length - 1];
                    if (latest) document.getElementById('cpu-value').textContent = latest.y.toFixed(1) + '%';
                }

                // Memory
                if (data['system_memory_percent']) {
                    const memData = data['system_memory_percent'].map(d => ({
                        x: d.timestamp * 1000,
                        y: d.value
                    }));
                    memChart.data.datasets[0].data = memData;
                    memChart.update('none');
                    const latest = memData[memData.length - 1];
                    if (latest) document.getElementById('mem-value').textContent = latest.y.toFixed(1) + '%';
                }

                // Network (calculate rate)
                if (data['system_network_bytes_sent_total'] && data['system_network_bytes_recv_total']) {
                    const sent = data['system_network_bytes_sent_total'];
                    const recv = data['system_network_bytes_recv_total'];

                    const netData = [];
                    for (let i = 1; i < sent.length && i < recv.length; i++) {
                        const dt = sent[i].timestamp - sent[i-1].timestamp;
                        if (dt > 0) {
                            const rate = ((sent[i].value - sent[i-1].value) + (recv[i].value - recv[i-1].value)) / dt / 1024 / 1024;
                            netData.push({ x: sent[i].timestamp * 1000, y: Math.max(0, rate) });
                        }
                    }
                    netChart.data.datasets[0].data = netData;
                    netChart.update('none');
                    const latest = netData[netData.length - 1];
                    if (latest) document.getElementById('net-value').textContent = latest.y.toFixed(2) + ' MB/s';
                }

                // Disk (calculate rate)
                if (data['system_disk_read_bytes_total'] && data['system_disk_write_bytes_total']) {
                    const read = data['system_disk_read_bytes_total'];
                    const write = data['system_disk_write_bytes_total'];

                    const diskData = [];
                    for (let i = 1; i < read.length && i < write.length; i++) {
                        const dt = read[i].timestamp - read[i-1].timestamp;
                        if (dt > 0) {
                            const rate = ((read[i].value - read[i-1].value) + (write[i].value - write[i-1].value)) / dt / 1024 / 1024;
                            diskData.push({ x: read[i].timestamp * 1000, y: Math.max(0, rate) });
                        }
                    }
                    diskChart.data.datasets[0].data = diskData;
                    diskChart.update('none');
                    const latest = diskData[diskData.length - 1];
                    if (latest) document.getElementById('disk-value').textContent = latest.y.toFixed(2) + ' MB/s';
                }
            } catch (err) {
                console.error('Failed to fetch metrics:', err);
            }
        }

        async function updateLogs() {
            try {
                const response = await fetch('/api/logs');
                const logs = await response.json();

                const container = document.getElementById('logs-container');
                document.getElementById('log-count').textContent = logs.length + ' entries';

                if (logs.length === 0) {
                    container.innerHTML = '<div class="log-entry"><span class="log-message">No logs yet...</span></div>';
                    return;
                }

                container.innerHTML = logs.map(log => {
                    const time = new Date(log.timestamp * 1000).toLocaleTimeString();
                    const attrs = Object.keys(log.attributes).length > 0
                        ? '<span class="log-attrs">' + JSON.stringify(log.attributes) + '</span>'
                        : '';
                    return `<div class="log-entry">
                        <span class="log-time">${time}</span>
                        <span class="log-level ${log.level}">${log.level}</span>
                        <span class="log-message">${log.message}</span>
                        ${attrs}
                    </div>`;
                }).join('');
            } catch (err) {
                console.error('Failed to fetch logs:', err);
            }
        }

        // Initial load and periodic updates
        updateCharts();
        updateLogs();
        setInterval(updateCharts, 2000);
        setInterval(updateLogs, 2000);
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Serve the dashboard HTML."""
    return HTMLResponse(content=DASHBOARD_HTML)
