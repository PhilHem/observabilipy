"""BDD test file for event observability features.

This file loads scenarios from feature files and generates test functions.
Step definitions are in conftest.py.
"""

import pytest
from pytest_bdd import scenarios

# Apply TRA markers to all BDD tests in this module
pytestmark = [
    pytest.mark.tra("Events.BDD"),
    pytest.mark.tier(0),
]

# Load all scenarios from feature files
# This generates test functions that pytest can discover
scenarios("event_mappings.feature")
scenarios("event_recording.feature")
scenarios("event_validation.feature")
