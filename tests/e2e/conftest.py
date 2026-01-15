"""Shared fixtures for E2E tests.

This module imports fixture plugins organized by concern:
- fixtures_storage: Storage adapters (in-memory and SQLite)
- fixtures_app: FastAPI application fixtures
- fixtures_policy: Retention policy fixtures
"""

# Import fixture modules to register fixtures with pytest
from tests.e2e.fixtures_app import *  # noqa: F403
from tests.e2e.fixtures_policy import *  # noqa: F403
from tests.e2e.fixtures_storage import *  # noqa: F403
