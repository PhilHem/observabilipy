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
    Structured logging via observabilipy provides searchable fields,
    correlation support, and JSON output for log aggregation.
"""

import asyncio
import os

import django
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

# Configure Django settings
if not settings.configured:
    secret_key = os.environ.get("DJANGO_SECRET_KEY", "example-key-not-for-production")
    settings.configure(
        DEBUG=True,
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        SECRET_KEY=secret_key,
    )
    django.setup()

from django.urls import path

from observabilipy import get_logger
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

# Application logger
logger = get_logger("django_example")


@instrument_view(metrics_storage, name="root")
async def root(_request: HttpRequest) -> HttpResponse:
    """Root endpoint with automatic metrics instrumentation.

    The @instrument_view decorator automatically records:
    - root_total counter (incremented on each request, with method and status labels)
    - root_duration_seconds histogram (request timing)
    """
    await logger.with_fields(endpoint="root").info("Root endpoint called")
    # Simulate some work
    await asyncio.sleep(0.01)
    return HttpResponse("Hello! Check /metrics and /logs endpoints.")


@instrument_view(metrics_storage, name="users_api", labels={"version": "v1"})
async def users_list(_request: HttpRequest) -> JsonResponse:
    """Users endpoint demonstrating instrumentation with custom labels.

    The decorator adds the HTTP method automatically. Custom labels like
    'version' are included in all metrics for this view.
    """
    await logger.with_fields(endpoint="users").info("Fetching users")
    # Simulate database fetch
    await asyncio.sleep(0.05)
    return JsonResponse(
        {
            "users": [
                {"id": "1", "name": "Alice"},
                {"id": "2", "name": "Bob"},
            ]
        }
    )


@instrument_view(metrics_storage)
async def error_demo(_request: HttpRequest) -> HttpResponse:
    """Error endpoint demonstrating error status in metrics.

    When the view name is not specified, the function name is used.
    When an exception occurs, the counter records status=error.
    """
    try:
        raise ValueError("Intentional error for demonstration")
    except ValueError:
        await logger.with_fields(endpoint="error_demo").error(
            "Error in error_demo endpoint"
        )
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
