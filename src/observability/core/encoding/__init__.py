"""Encoding modules for observability data."""

from observability.core.encoding.ndjson import encode_logs
from observability.core.encoding.prometheus import encode_metrics

__all__ = ["encode_logs", "encode_metrics"]
