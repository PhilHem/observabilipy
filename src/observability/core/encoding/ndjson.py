"""NDJSON encoder for log entries."""

import json
from collections.abc import Iterable

from observability.core.models import LogEntry


def encode_logs(entries: Iterable[LogEntry]) -> str:
    """Encode log entries to newline-delimited JSON.

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
