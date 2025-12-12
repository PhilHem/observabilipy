"""ASGI generic adapter for observability endpoints.

This adapter provides a framework-agnostic ASGI application that can be used
with any ASGI server (uvicorn, hypercorn, daphne) without requiring FastAPI
or Django as dependencies.
"""

from collections.abc import Callable, Coroutine
from typing import Any
from urllib.parse import parse_qs

from observabilipy.core.encoding.ndjson import encode_logs, encode_ndjson
from observabilipy.core.encoding.prometheus import encode_current
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

# ASGI type aliases
Scope = dict[str, Any]
Receive = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
Send = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
ASGIApp = Callable[[Scope, Receive, Send], Coroutine[Any, Any, None]]


def create_asgi_app(
    log_storage: LogStoragePort,
    metrics_storage: MetricsStoragePort,
) -> ASGIApp:
    """Create an ASGI app with /metrics, /metrics/prometheus, and /logs endpoints.

    Args:
        log_storage: Storage adapter implementing LogStoragePort.
        metrics_storage: Storage adapter implementing MetricsStoragePort.

    Returns:
        ASGI application callable.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return

        path = scope["path"]

        if path == "/metrics":
            headers = [(b"content-type", b"application/x-ndjson")]
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            since = float(params.get("since", ["0"])[0])
            body = await encode_ndjson(metrics_storage.read(since=since))
            await send(
                {"type": "http.response.start", "status": 200, "headers": headers}
            )
            await send({"type": "http.response.body", "body": body.encode()})
        elif path == "/metrics/prometheus":
            headers = [(b"content-type", b"text/plain; version=0.0.4; charset=utf-8")]
            body = await encode_current(metrics_storage.read())
            await send(
                {"type": "http.response.start", "status": 200, "headers": headers}
            )
            await send({"type": "http.response.body", "body": body.encode()})
        elif path == "/logs":
            headers = [(b"content-type", b"application/x-ndjson")]
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            since = float(params.get("since", ["0"])[0])
            level_list = params.get("level", [None])
            level = level_list[0] if level_list else None
            body = await encode_logs(log_storage.read(since=since, level=level))
            await send(
                {"type": "http.response.start", "status": 200, "headers": headers}
            )
            await send({"type": "http.response.body", "body": body.encode()})
        else:
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"Not Found"})

    return app
