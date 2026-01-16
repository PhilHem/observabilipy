"""WSGI generic adapter for observability endpoints.

This adapter provides a framework-agnostic WSGI application that can be used
with any WSGI server (gunicorn, uWSGI, waitress) or framework (Flask, Bottle)
without requiring additional dependencies.

Note: The event loop is created once per app instance (at factory time) and
reused across requests. This moves concurrency control to the application
boundary rather than creating a new loop per request.
"""

from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import parse_qs

from observabilipy.adapters.frameworks.query_params import (
    _parse_level_param,
    _parse_since_param,
)
from observabilipy.adapters.storage import collect_async_iterable
from observabilipy.core.encoding.ndjson import encode_logs_sync, encode_ndjson_sync
from observabilipy.core.encoding.prometheus import encode_current_sync
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

# WSGI type aliases
StartResponse = Callable[[str, list[tuple[str, str]]], Callable[[bytes], object]]
WSGIApp = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]


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
            since = _parse_since_param(params)
            samples = collect_async_iterable(metrics_storage.read(since=since))
            body = encode_ndjson_sync(samples)
            start_response("200 OK", headers)
            return [body.encode()]
        if path == "/metrics/prometheus":
            headers = [("Content-Type", "text/plain; version=0.0.4; charset=utf-8")]
            samples = collect_async_iterable(metrics_storage.read())
            body = encode_current_sync(samples)
            start_response("200 OK", headers)
            return [body.encode()]
        if path == "/logs":
            headers = [("Content-Type", "application/x-ndjson")]
            query_string = environ.get("QUERY_STRING", "")
            params = parse_qs(query_string)
            since = _parse_since_param(params)
            level = _parse_level_param(params)
            log_entries = log_storage.read(since=since, level=level)
            entries = collect_async_iterable(log_entries)
            body = encode_logs_sync(entries)
            start_response("200 OK", headers)
            return [body.encode()]
        start_response("404 Not Found", [])
        return [b"Not Found"]

    return app
