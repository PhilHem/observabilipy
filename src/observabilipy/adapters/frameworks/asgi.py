"""ASGI generic adapter for observability endpoints.

This adapter provides a framework-agnostic ASGI application that can be used
with any ASGI server (uvicorn, hypercorn, daphne) without requiring FastAPI
or Django as dependencies.
"""

import fnmatch
import json
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any
from urllib.parse import parse_qs

from observabilipy.adapters.frameworks.query_params import (
    _parse_level_param,
    _parse_since_param,
)
from observabilipy.adapters.logging_context import clear_log_context, set_log_context
from observabilipy.core.encoding.ndjson import encode_logs, encode_ndjson
from observabilipy.core.encoding.prometheus import encode_current
from observabilipy.core.logs import log_exception
from observabilipy.core.models import LogEntry, MetricSample
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

# ASGI type aliases
# @tra: Adapter.ASGI.Fixtures.BasicApp
# @tra: Adapter.ASGI.Fixtures.Scope
# @tra: Adapter.ASGI.Fixtures.SendCapture
Scope = dict[str, Any]
Receive = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
Send = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
ASGIApp = Callable[[Scope, Receive, Send], Coroutine[Any, Any, None]]


def _parse_query_params(scope: Scope) -> dict[str, list[str]]:
    """Parse query string from ASGI scope into parameter dictionary.

    Args:
        scope: ASGI scope dictionary containing request metadata.

    Returns:
        Dictionary mapping parameter names to lists of values.
        Returns empty dict if query_string is missing or empty.
    """
    # @tra: Adapter.ASGI.QueryParameter.Parser
    query_string = scope.get("query_string", b"").decode(errors="replace")
    return parse_qs(query_string)


def _extract_request_id(scope: Scope, header_name: str = "X-Request-ID") -> str:
    """Extract or generate a request ID from ASGI scope headers.

    Searches for the specified header (case-insensitive). If not found,
    generates a new UUID.

    Args:
        scope: ASGI scope dictionary containing request metadata.
        header_name: Name of the header to search for (default: "X-Request-ID").

    Returns:
        Request ID string (either from header or newly generated UUID).
    """
    # @tra: Adapter.ASGI.Middleware.RequestId.Extract
    header_bytes = header_name.lower().encode()
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    for name, value in headers:
        if name.lower() == header_bytes:
            return str(value.decode("utf-8", errors="replace"))

    # @tra: Adapter.ASGI.Middleware.RequestId.Generate
    return str(uuid.uuid4())


def _get_log_level_for_status(status_code: int) -> str:
    """Determine log level based on HTTP status code.

    Maps status codes to log levels:
    - 200-299 (2xx) → "INFO"
    - 400-499 (4xx) → "WARN"
    - 500-599 (5xx) → "ERROR"
    - Other → "INFO" (default)

    Args:
        status_code: HTTP status code from response.

    Returns:
        Log level string ("INFO", "WARN", or "ERROR").
    """
    # @tra: Adapter.ASGI.Middleware.LogLevels
    if 200 <= status_code < 300:
        return "INFO"
    if 400 <= status_code < 500:
        return "WARN"
    if 500 <= status_code < 600:
        return "ERROR"
    return "INFO"


async def _send_response(send: Send, status: int, content_type: str, body: str) -> None:
    """Send an HTTP response with headers and body.

    Args:
        send: ASGI send callable for writing response.
        status: HTTP status code.
        content_type: Content-Type header value.
        body: Response body as string (will be encoded to bytes).
    """
    # @tra: Adapter.ASGI.SendResponse.Headers
    headers = [(b"content-type", content_type.encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    # @tra: Adapter.ASGI.SendResponse.Body
    await send({"type": "http.response.body", "body": body.encode()})


async def _handle_endpoint(
    send: Send,
    endpoint_func: Callable[[], Coroutine[Any, Any, str]],
    content_type: str,
    log_message: str,
) -> None:
    """Execute an endpoint function with error handling and send response.

    Args:
        send: ASGI send callable for writing response.
        endpoint_func: Async function that returns response body.
        content_type: Content-Type header for success response.
        log_message: Message to log on error.
    """
    try:
        body = await endpoint_func()
        await _send_response(send, 200, content_type, body)
    except Exception:
        log_exception(log_message)
        error_body = json.dumps({"error": "Internal Server Error"})
        await _send_response(send, 500, "application/json", error_body)


# @tra: Adapter.ASGI.Middleware.Init
# @tra: Adapter.ASGI.Middleware.Interface
# @tra: Adapter.ASGI.Middleware.Passthrough
class ASGIObservabilityMiddleware:
    """ASGI middleware that wraps applications to capture observability.

    This middleware intercepts ASGI requests to automatically log request
    details and capture timing metrics.
    """

    def __init__(
        self,
        app: ASGIApp,
        log_storage: LogStoragePort | None,
        metrics_storage: MetricsStoragePort | None,
        exclude_paths: list[str] | None = None,
        request_id_header: str = "X-Request-ID",
    ) -> None:
        """Initialize the middleware with a wrapped app and storage adapters.

        Args:
            app: The ASGI application to wrap.
            log_storage: Storage adapter for logs (optional).
            metrics_storage: Storage adapter for metrics (optional).
            exclude_paths: List of paths to exclude from logging/metrics.
                          Supports exact matches and wildcard patterns
                          (e.g., "/internal/*").
            request_id_header: Name of the header to extract request ID from
                             (default: "X-Request-ID").
        """
        self.app = app
        self.log_storage = log_storage
        self.metrics_storage = metrics_storage
        self.exclude_paths = exclude_paths or []
        self.request_id_header = request_id_header
        self.log_requests = True
        self.record_metrics = True
        self.request_counter_name = "http_requests_total"
        self.request_histogram_name = "http_request_duration_seconds"

    def set_log_requests(self, enabled: bool) -> None:
        """Set whether to log requests.

        Args:
            enabled: True to enable request logging, False to disable.
                    Metrics are always recorded regardless of this setting.
        """
        self.log_requests = enabled

    def set_record_metrics(self, enabled: bool) -> None:
        """Set whether to record metrics.

        Args:
            enabled: True to enable metrics recording, False to disable.
                    Logs are always recorded regardless of this setting.
        """
        self.record_metrics = enabled

    def set_request_counter_name(self, name: str) -> None:
        """Set the name for the request counter metric.

        Args:
            name: Custom name for the HTTP request counter metric
                 (default: "http_requests_total").
        """
        self.request_counter_name = name

    def set_request_histogram_name(self, name: str) -> None:
        """Set the name for the request histogram metric.

        Args:
            name: Custom name for the HTTP request duration histogram metric
                 (default: "http_request_duration_seconds").
        """
        self.request_histogram_name = name

    def _path_excluded(self, path: str) -> bool:
        """Check if path matches any pattern in exclude_paths."""
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.exclude_paths)

    async def _write_log_entry(
        self, scope: Scope, request_data: dict[str, Any]
    ) -> None:
        """Write request log entry if logging is enabled."""
        if not self.log_requests or self.log_storage is None:
            return
        log_level = _get_log_level_for_status(request_data["status_code"])
        log_entry = LogEntry(
            timestamp=time.time(),
            level=log_level,
            message=f"{scope['method']} {scope['path']}",
            attributes=request_data,
        )
        await self.log_storage.write(log_entry)

    async def _write_metrics(
        self, scope: Scope, status_code: int, duration: float
    ) -> None:
        """Write request metrics if metrics recording is enabled."""
        if not self.record_metrics or self.metrics_storage is None:
            return
        counter_metric = MetricSample(
            name=self.request_counter_name,
            timestamp=time.time(),
            value=1.0,
            labels={
                "method": scope["method"],
                "path": scope["path"],
                "status": str(status_code),
            },
        )
        await self.metrics_storage.write(counter_metric)
        histogram_metric = MetricSample(
            name=self.request_histogram_name,
            timestamp=time.time(),
            value=duration,
            labels={"method": scope["method"], "path": scope["path"]},
        )
        await self.metrics_storage.write(histogram_metric)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable interface that processes requests through the wrapped app."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        request_id = _extract_request_id(scope, self.request_id_header)
        captured: dict[str, Any] = {"status": None, "body_size": 0, "exception": None}

        async def wrapped_send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                captured["status"] = message["status"]
            elif message["type"] == "http.response.body":
                captured["body_size"] += len(message.get("body", b""))
            await send(message)

        set_log_context(request_id=request_id)
        try:
            await self.app(scope, receive, wrapped_send)
        except Exception as e:
            captured["exception"] = e
            captured["status"] = 500
        finally:
            clear_log_context()

        duration = time.perf_counter() - start_time
        await self._record_observability(scope, request_id, captured, duration)
        if captured["exception"] is not None:
            raise captured["exception"]

    async def _record_observability(
        self,
        scope: Scope,
        request_id: str,
        captured: dict[str, Any],
        duration: float,
    ) -> None:
        """Record logs and metrics for the request."""
        if self._path_excluded(scope["path"]):
            return
        request_data: dict[str, Any] = {
            "request_id": request_id,
            "method": scope["method"],
            "path": scope["path"],
            "status_code": captured["status"] or 0,
            "response_body_size": captured["body_size"],
            "duration_ms": duration * 1000,
        }
        if captured["exception"] is not None:
            exc = captured["exception"]
            request_data["exception"] = f"{type(exc).__name__}: {exc!s}"
        await self._write_log_entry(scope, request_data)
        if captured["status"] is not None:
            await self._write_metrics(scope, captured["status"], duration)


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

        # @tra: Adapter.ASGI.MetricsEndpointHTTPStatus
        # @tra: Adapter.ASGI.MetricsEndpointContentType
        # @tra: Adapter.ASGI.MetricsEndpointNDJSON
        # @tra: Adapter.ASGI.MetricsEndpointSinceFilter
        # @tra: Adapter.ASGI.MetricsEndpointEncodingError
        if path == "/metrics":
            params = _parse_query_params(scope)
            since = _parse_since_param(params)
            await _handle_endpoint(
                send,
                lambda: encode_ndjson(metrics_storage.read(since=since)),
                "application/x-ndjson",
                "Error encoding metrics endpoint",
            )
        # @tra: Adapter.ASGI.PrometheusEndpointHTTPStatus
        # @tra: Adapter.ASGI.PrometheusEndpointContentType
        # @tra: Adapter.ASGI.PrometheusEndpointFormat
        # @tra: Adapter.ASGI.PrometheusEndpointCurrent
        elif path == "/metrics/prometheus":
            body = await encode_current(metrics_storage.read())
            await _send_response(
                send, 200, "text/plain; version=0.0.4; charset=utf-8", body
            )
        # @tra: Adapter.ASGI.LogsEndpointHTTPStatus
        # @tra: Adapter.ASGI.LogsEndpointContentType
        # @tra: Adapter.ASGI.LogsEndpointNDJSON
        # @tra: Adapter.ASGI.LogsEndpointSinceFilter
        # @tra: Adapter.ASGI.LogsEndpointLevelFilter
        # @tra: Adapter.ASGI.LogsEndpointEncodingError
        elif path == "/logs":
            params = _parse_query_params(scope)
            since = _parse_since_param(params)
            level = _parse_level_param(params)
            await _handle_endpoint(
                send,
                lambda: encode_logs(log_storage.read(since=since, level=level)),
                "application/x-ndjson",
                "Error encoding logs endpoint",
            )
        # @tra: Adapter.ASGI.RoutingUnknownPath
        else:
            await _send_response(send, 404, "text/plain", "Not Found")

    return app
