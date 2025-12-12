"""WSGI generic adapter for observability endpoints.

This adapter provides a framework-agnostic WSGI application that can be used
with any WSGI server (gunicorn, uWSGI, waitress) or framework (Flask, Bottle)
without requiring additional dependencies.
"""

import asyncio
from collections.abc import AsyncIterable, Callable, Iterable
from typing import Any
from urllib.parse import parse_qs

from observabilipy.core.encoding.ndjson import encode_logs_sync, encode_ndjson_sync
from observabilipy.core.encoding.prometheus import encode_current_sync
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

# WSGI type aliases
StartResponse = Callable[[str, list[tuple[str, str]]], Callable[[bytes], object]]
WSGIApp = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]


async def _collect_async[T](iterable: AsyncIterable[T]) -> list[T]:
    """Collect all items from an async iterable into a list."""
    return [item async for item in iterable]


def create_wsgi_app(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
) -> WSGIApp:
    """Create a WSGI app with /metrics, /metrics/prometheus, and /logs endpoints.

    Args:
        log_storage: Storage adapter implementing LogStoragePort.
        metrics_storage: Storage adapter implementing MetricsStoragePort.

    Returns:
        WSGI application callable.
    """

    def app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        path = environ.get("PATH_INFO", "/")

        if path == "/metrics":
            headers = [("Content-Type", "application/x-ndjson")]
            query_string = environ.get("QUERY_STRING", "")
            params = parse_qs(query_string)
            since = float(params.get("since", ["0"])[0])
            samples = asyncio.run(_collect_async(metrics_storage.read(since=since)))
            body = encode_ndjson_sync(samples)
            start_response("200 OK", headers)
            return [body.encode()]
        elif path == "/metrics/prometheus":
            headers = [("Content-Type", "text/plain; version=0.0.4; charset=utf-8")]
            samples = asyncio.run(_collect_async(metrics_storage.read()))
            body = encode_current_sync(samples)
            start_response("200 OK", headers)
            return [body.encode()]
        elif path == "/logs":
            headers = [("Content-Type", "application/x-ndjson")]
            query_string = environ.get("QUERY_STRING", "")
            params = parse_qs(query_string)
            since = float(params.get("since", ["0"])[0])
            level_list = params.get("level", [None])
            level = level_list[0] if level_list else None
            log_entries = log_storage.read(since=since, level=level)
            entries = asyncio.run(_collect_async(log_entries))
            body = encode_logs_sync(entries)
            start_response("200 OK", headers)
            return [body.encode()]
        else:
            start_response("404 Not Found", [])
            return [b"Not Found"]

    return app
