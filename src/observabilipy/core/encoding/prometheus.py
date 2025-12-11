"""Prometheus text format encoder for metric samples."""

from collections.abc import AsyncIterable

from observabilipy.core.models import MetricSample


def _escape_label_value(value: str) -> str:
    """Escape special characters in label values per Prometheus spec.

    Escapes: backslash -> \\, double quote -> \", newline -> \n
    """
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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
