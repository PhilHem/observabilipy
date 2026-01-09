"""BDD test file for event observability features.

This file loads scenarios from feature files and generates test functions.
Step definitions are in conftest.py.
"""

from pytest_bdd import scenarios

# Load all scenarios from feature files
# This generates test functions that pytest can discover
scenarios("event_mappings.feature")
scenarios("event_recording.feature")
scenarios("event_validation.feature")
