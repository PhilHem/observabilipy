"""Prometheus text format encoder for metric samples."""

from collections.abc import AsyncIterable, Iterable

from observabilipy.core.models import MetricSample


def _escape_label_value(value: str) -> str:
    """Escape special characters in label values per Prometheus spec.

    Escapes: backslash -> \\, double quote -> \", newline -> \n
    """
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def encode_metrics_sync(samples: Iterable[MetricSample]) -> str:
    """Encode metric samples to Prometheus text format (synchronous version).

    Args:
        samples: An iterable of MetricSample objects.

    Returns:
        Prometheus text format string with one metric per line.
        Empty string if no samples.

    Example:
        >>> from observabilipy import MetricSample
        >>> s = MetricSample(name="req", timestamp=1.0, value=42.0, labels={"m": "GET"})
        >>> output = encode_metrics_sync([s])
        >>> 'req{m="GET"} 42.0' in output
        True
    """
    lines = []
    for sample in samples:
        # Build label string if labels exist
        if sample.labels:
            label_pairs = [
                f'{k}="{_escape_label_value(v)}"'
                for k, v in sorted(sample.labels.items())
            ]
            label_str = "{" + ",".join(label_pairs) + "}"
        else:
            label_str = ""

        # Convert timestamp from seconds to milliseconds
        timestamp_ms = int(sample.timestamp * 1000)

        lines.append(f"{sample.name}{label_str} {sample.value} {timestamp_ms}")

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


def encode_current_sync(samples: Iterable[MetricSample]) -> str:
    """Encode metric samples, keeping only the latest sample per metric (sync version).

    This is intended for Prometheus scrape endpoints where each metric
    (identified by name + labels) should appear only once with its
    most recent value.

    Args:
        samples: An iterable of MetricSample objects.

    Returns:
        Prometheus text format string with one line per unique metric.
        Empty string if no samples.

    Example:
        >>> from observabilipy import MetricSample
        >>> samples = [
        ...     MetricSample(name="temp", timestamp=1.0, value=20.0, labels={}),
        ...     MetricSample(name="temp", timestamp=2.0, value=25.0, labels={}),
        ... ]
        >>> output = encode_current_sync(samples)
        >>> "25.0" in output and "20.0" not in output
        True
    """
    latest: dict[tuple[str, frozenset[tuple[str, str]]], MetricSample] = {}

    for sample in samples:
        key = (sample.name, frozenset(sample.labels.items()))
        existing = latest.get(key)
        if existing is None or sample.timestamp > existing.timestamp:
            latest[key] = sample

    return encode_metrics_sync(latest.values())


async def encode_metrics(samples: AsyncIterable[MetricSample]) -> str:
    """Encode metric samples to Prometheus text format.

    Args:
        samples: An async iterable of MetricSample objects.

    Returns:
        Prometheus text format string with one metric per line.
        Empty string if no samples.
    """
    lines = []
    async for sample in samples:
        # Build label string if labels exist
        if sample.labels:
            label_pairs = [
                f'{k}="{_escape_label_value(v)}"'
                for k, v in sorted(sample.labels.items())
            ]
            label_str = "{" + ",".join(label_pairs) + "}"
        else:
            label_str = ""

        # Convert timestamp from seconds to milliseconds
        timestamp_ms = int(sample.timestamp * 1000)

        lines.append(f"{sample.name}{label_str} {sample.value} {timestamp_ms}")

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


async def encode_current(samples: AsyncIterable[MetricSample]) -> str:
    """Encode metric samples, keeping only the latest sample per metric.

    This is intended for Prometheus scrape endpoints where each metric
    (identified by name + labels) should appear only once with its
    most recent value.

    Args:
        samples: An async iterable of MetricSample objects.

    Returns:
        Prometheus text format string with one line per unique metric.
        Empty string if no samples.
    """
    latest: dict[tuple[str, frozenset[tuple[str, str]]], MetricSample] = {}

    async for sample in samples:
        key = (sample.name, frozenset(sample.labels.items()))
        existing = latest.get(key)
        if existing is None or sample.timestamp > existing.timestamp:
            latest[key] = sample

    return encode_metrics_sync(latest.values())
