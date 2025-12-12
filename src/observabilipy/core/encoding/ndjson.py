"""NDJSON encoder for log entries."""

import json
from collections.abc import AsyncIterable, Iterable

from observabilipy.core.models import LogEntry


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
