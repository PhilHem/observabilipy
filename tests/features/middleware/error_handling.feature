Feature: Middleware Error Handling
  As a service operator
  I want errors captured without breaking the application
  So that observability never causes outages

  Background:
    Given in-memory log storage
    And in-memory metrics storage
    And an ASGI app with observability middleware

  Scenario: Unhandled endpoint exception is logged and re-raised
    Given an endpoint that raises ValueError("bad input")
    When a request is made to that endpoint
    Then an ERROR log should be recorded with exception details
    And the ValueError should still propagate to the client
    And status_code should be 500

  Scenario: Storage failure does not break the request
    Given log storage that raises IOError on write
    When a request is made
    Then the request should complete successfully
    And the response should be returned to the client
    And a warning should be logged to stderr

  Scenario: Middleware timeout does not block request
    Given log storage that hangs for 30 seconds
    And middleware configured with write_timeout=100ms
    When a request is made
    Then the request should complete within 200ms
    And the response should be returned

  Scenario: Exception in context cleanup does not mask original error
    Given an endpoint that raises RuntimeError
    And context cleanup that also raises an error
    When a request is made
    Then the RuntimeError should be raised to the client
    And the cleanup error should be logged separately
