"""Example Django application with observability endpoints.

Note: This example requires ASGI. The adapter uses async views.

Run with:
    uvicorn examples.django_example:application --reload

Then visit:
    http://localhost:8000/metrics - Prometheus metrics
    http://localhost:8000/logs - NDJSON logs
    http://localhost:8000/logs?since=0 - Logs since timestamp
"""

import time

import django
from django.conf import settings
from django.http import HttpRequest, HttpResponse

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

from observability.adapters.frameworks.django import create_observability_urlpatterns
from observability.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observability.core.models import LogEntry, MetricSample

# Create storage instances
log_storage = InMemoryLogStorage()
metrics_storage = InMemoryMetricsStorage()


async def root(request: HttpRequest) -> HttpResponse:
    """Root endpoint that logs a message and increments a counter."""
    # Log the request
    await log_storage.write(
        LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Root endpoint called",
            attributes={"path": "/"},
        )
    )

    # Record a metric
    await metrics_storage.write(
        MetricSample(
            name="http_requests_total",
            timestamp=time.time(),
            value=1.0,
            labels={"method": "GET", "path": "/"},
        )
    )

    return HttpResponse("Hello! Check /metrics and /logs endpoints.")


# URL patterns
urlpatterns = [
    path("", root, name="root"),
    *create_observability_urlpatterns(log_storage, metrics_storage),
]


# ASGI application for uvicorn
def get_asgi_application():
    from django.core.asgi import get_asgi_application as django_asgi

    return django_asgi()


application = get_asgi_application()
