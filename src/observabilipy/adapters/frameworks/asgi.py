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
from observabilipy.core.logs import log_exception
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort

# ASGI type aliases
# @tra: Adapter.ASGI.Fixtures.BasicApp
# @tra: Adapter.ASGI.Fixtures.Scope
# @tra: Adapter.ASGI.Fixtures.SendCapture
Scope = dict[str, Any]
Receive = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
Send = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
ASGIApp = Callable[[Scope, Receive, Send], Coroutine[Any, Any, None]]

# Valid log levels for validation
VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


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


def _parse_since_param(params: dict[str, list[str]]) -> float:
    """Parse and validate the 'since' query parameter.

    Args:
        params: Parsed query string parameters.

    Returns:
        Timestamp as float, defaulting to 0.0 if invalid or missing.
    """
    # @tra: Adapter.ASGI.QueryParameter.InvalidUTF8
    try:
        return float(params.get("since", ["0"])[0])
    except ValueError:
        return 0.0


def _parse_level_param(params: dict[str, list[str]]) -> str | None:
    """Parse and validate the 'level' query parameter.

    Args:
        params: Parsed query string parameters.

    Returns:
        Validated level string (uppercase) or None if invalid/missing.
    """
    # @tra: Adapter.ASGI.QueryParameter.InvalidUTF8
    level_list = params.get("level", [None])
    level_raw = level_list[0] if level_list else None
    if level_raw and level_raw.upper() in VALID_LEVELS:
        return level_raw.upper()
    return None


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
        log_storage: LogStoragePort,
        metrics_storage: MetricsStoragePort,
    ) -> None:
        """Initialize the middleware with a wrapped app and storage adapters.

        Args:
            app: The ASGI application to wrap.
            log_storage: Storage adapter for logs.
            metrics_storage: Storage adapter for metrics.
        """
        self.app = app
        self.log_storage = log_storage
        self.metrics_storage = metrics_storage

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable interface that processes requests through the wrapped app.

        For now, this simply passes through to the wrapped application.
        Future enhancements will add request timing and logging.

        Args:
            scope: ASGI scope dictionary containing request metadata.
            receive: ASGI receive callable for reading request body.
            send: ASGI send callable for writing response.
        """
        # For now, just pass through to wrapped app
        # Future: Add timing, logging, and metrics capture here
        await self.app(scope, receive, send)


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
            try:
                body = await encode_ndjson(metrics_storage.read(since=since))
                await _send_response(send, 200, "application/x-ndjson", body)
            except Exception:
                log_exception("Error encoding metrics endpoint")
                error_body = "Internal Server Error"
                await _send_response(send, 500, "application/x-ndjson", error_body)
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
            try:
                body = await encode_logs(log_storage.read(since=since, level=level))
                await _send_response(send, 200, "application/x-ndjson", body)
            except Exception:
                log_exception("Error encoding logs endpoint")
                error_body = "Internal Server Error"
                await _send_response(send, 500, "application/x-ndjson", error_body)
        # @tra: Adapter.ASGI.RoutingUnknownPath
        else:
            await _send_response(send, 404, "text/plain", "Not Found")

    return app
