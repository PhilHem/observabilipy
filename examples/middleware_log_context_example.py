"""Example: FastAPI middleware with log_context for request ID injection.

This example demonstrates the recommended pattern for adding request-scoped
context (like request IDs, user IDs, correlation IDs) to all logs within a
request lifecycle using observabilipy's log_context helper.

The key benefit: you don't need to pass `extra={"request_id": ...}` to every
logging call. The context is automatically included via the context_provider.

Run with:
    uvicorn examples.middleware_log_context_example:app --reload

Test with:
    # Make a request with custom request ID
    curl -H "X-Request-ID: my-request-123" http://localhost:8000/

    # Make a request without (generates UUID)
    curl http://localhost:8000/users/42

    # View logs with request context
    curl http://localhost:8000/logs

Each log entry will include request_id, method, and path automatically.
"""

import logging
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from observabilipy import (
    ObservabilipyHandler,
    get_log_context,
    log_context,
)
from observabilipy.adapters.frameworks.fastapi import create_observability_router
from observabilipy.adapters.storage.in_memory import InMemoryLogStorage

# Create storage for logs
log_storage = InMemoryLogStorage()

# Configure Python logging with observabilipy handler
# The context_provider=get_log_context is the key - it pulls in context
# set via log_context() automatically for every log entry
handler = ObservabilipyHandler(log_storage, context_provider=get_log_context)
logging.basicConfig(level=logging.INFO)
logging.getLogger().addHandler(handler)

# Application logger
logger = logging.getLogger("middleware_example")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request context into all logs.

    This middleware wraps each request in a log_context() that automatically
    adds request_id, method, and path to every log entry made during the
    request lifecycle - including logs from nested function calls.
    """

    async def dispatch(self, request: Request, call_next):
        # Extract request ID from header, or generate a new UUID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # All logs within this context block will automatically include
        # these attributes without needing to pass extra={} to each call
        with log_context(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        ):
            logger.info("Request started")
            response = await call_next(request)
            logger.info("Request completed", extra={"status_code": response.status_code})
            return response


# Create FastAPI app
app = FastAPI(title="Middleware Log Context Example")

# Add our request context middleware
app.add_middleware(RequestContextMiddleware)

# Mount observability endpoints (/logs, /metrics)
app.include_router(create_observability_router(log_storage, None))

logger.info("Application initialized")


@app.get("/")
async def root():
    """Root endpoint - logs will automatically include request context."""
    logger.info("Processing root endpoint")
    return {
        "message": "Hello! Check /logs to see request context in your logs.",
        "tip": "Try: curl -H 'X-Request-ID: test-123' http://localhost:8000/",
    }


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """User endpoint - demonstrates nested context.

    The handler adds user_id to the context, which combines with the
    request_id already set by the middleware.
    """
    # Add user_id to context for logs within this handler
    with log_context(user_id=user_id):
        logger.info("Fetching user from database")
        # Simulate some work
        logger.info("User found")

    return {"user_id": user_id, "name": "Example User"}


@app.get("/error")
async def error_endpoint():
    """Error endpoint - demonstrates context preserved through exceptions."""
    logger.info("About to raise an error")
    try:
        raise ValueError("Intentional error for demonstration")
    except ValueError:
        logger.exception("Error occurred during request")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
