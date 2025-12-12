"""NDJSON encoder for log entries and metric samples."""

import json
from collections.abc import AsyncIterable, Iterable

from observabilipy.core.models import LogEntry, MetricSample


def encode_logs_sync(entries: Iterable[LogEntry]) -> str:
    """Encode log entries to newline-delimited JSON (synchronous version).

    Args:
        entries: An iterable of LogEntry objects.

    Returns:
        NDJSON string with one JSON object per line.
        Empty string if no entries.
    """
    lines = []
    for entry in entries:
        obj = {
            "timestamp": entry.timestamp,
            "level": entry.level,
            "message": entry.message,
            "attributes": entry.attributes,
        }
        lines.append(json.dumps(obj))

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


async def encode_logs(entries: AsyncIterable[LogEntry]) -> str:
    """Encode log entries to newline-delimited JSON.

    Args:
        entries: An async iterable of LogEntry objects.

    Returns:
        NDJSON string with one JSON object per line.
        Empty string if no entries.
    """
    lines = []
    async for entry in entries:
        obj = {
            "timestamp": entry.timestamp,
            "level": entry.level,
            "message": entry.message,
            "attributes": entry.attributes,
        }
        lines.append(json.dumps(obj))

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


def encode_ndjson_sync(samples: Iterable[MetricSample]) -> str:
    """Encode metric samples to newline-delimited JSON (synchronous version).

    Args:
        samples: An iterable of MetricSample objects.

    Returns:
        NDJSON string with one JSON object per line.
        Empty string if no samples.
    """
    lines = []
    for sample in samples:
        obj = {
            "name": sample.name,
            "timestamp": sample.timestamp,
            "value": sample.value,
            "labels": sample.labels,
        }
        lines.append(json.dumps(obj))

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


async def encode_ndjson(samples: AsyncIterable[MetricSample]) -> str:
    """Encode metric samples to newline-delimited JSON.

    Args:
        samples: An async iterable of MetricSample objects.

    Returns:
        NDJSON string with one JSON object per line.
        Empty string if no samples.
    """
    lines = []
    async for sample in samples:
        obj = {
            "name": sample.name,
            "timestamp": sample.timestamp,
            "value": sample.value,
            "labels": sample.labels,
        }
        lines.append(json.dumps(obj))

    if not lines:
        return ""

    return "\n".join(lines) + "\n"
