"""BDD tests for middleware observability features."""

import pytest
from pytest_bdd import scenarios

# Load all middleware feature scenarios
scenarios(".")

# Apply TRA markers for middleware tests
pytestmark = [
    pytest.mark.tier(2),  # Integration tests require ASGI setup
    pytest.mark.tra("Adapter.Middleware.AutoInstrumentation"),
]
