"""Example Django application with observability endpoints.

Note: This example requires ASGI. The adapter uses async views.

Run with:
    uvicorn examples.django_example:application --reload

Then visit:
    http://localhost:8000/           - Root endpoint (instrumented)
    http://localhost:8000/users      - Users endpoint (instrumented)
    http://localhost:8000/metrics    - NDJSON metrics
    http://localhost:8000/metrics/prometheus - Prometheus text format
    http://localhost:8000/logs       - NDJSON logs

Instrumentation:
    This example demonstrates automatic metrics collection using the
    `@instrument_view` decorator for Django async views.

Logging Integration:
    Python's standard logging is bridged to observabilipy using
    ObservabilipyHandler, so all logs appear in /logs endpoint.
"""

import asyncio
import logging

import django
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        SECRET_KEY="example-secret-key-not-for-production",
    )
    django.setup()

from django.urls import path

from observabilipy import ObservabilipyHandler
from observabilipy.adapters.frameworks.django import (
    create_observability_urlpatterns,
    instrument_view,
)
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)

# Create storage instances
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()

# Bridge Python logging to observabilipy
logging.basicConfig(level=logging.INFO)
handler = ObservabilipyHandler(log_storage)
logging.getLogger().addHandler(handler)

# Application logger
logger = logging.getLogger("django_example")
logger.info("Django application initialized")


@instrument_view(metrics_storage, name="root")
async def root(request: HttpRequest) -> HttpResponse:
    """Root endpoint with automatic metrics instrumentation.

    The @instrument_view decorator automatically records:
    - root_total counter (incremented on each request, with method and status labels)
    - root_duration_seconds histogram (request timing)
    """
    logger.info("Root endpoint called")
    # Simulate some work
    await asyncio.sleep(0.01)
    return HttpResponse("Hello! Check /metrics and /logs endpoints.")


@instrument_view(metrics_storage, name="users_api", labels={"version": "v1"})
async def users_list(request: HttpRequest) -> JsonResponse:
    """Users endpoint demonstrating instrumentation with custom labels.

    The decorator adds the HTTP method automatically. Custom labels like
    'version' are included in all metrics for this view.
    """
    logger.info("Fetching users", extra={"endpoint": "users"})
    # Simulate database fetch
    await asyncio.sleep(0.05)
    return JsonResponse({
        "users": [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
        ]
    })


@instrument_view(metrics_storage)
async def error_demo(request: HttpRequest) -> HttpResponse:
    """Error endpoint demonstrating error status in metrics.

    When the view name is not specified, the function name is used.
    When an exception occurs, the counter records status=error.
    The exception is also captured in the logs via logger.exception().
    """
    try:
        raise ValueError("Intentional error for demonstration")
    except ValueError:
        logger.exception("Error in error_demo endpoint")
        raise


# URL patterns
urlpatterns = [
    path("", root, name="root"),
    path("users", users_list, name="users"),
    path("error", error_demo, name="error"),
    *create_observability_urlpatterns(log_storage, metrics_storage),
]


# ASGI application for uvicorn
def get_asgi_application():
    from django.core.asgi import get_asgi_application as django_asgi

    return django_asgi()


application = get_asgi_application()
