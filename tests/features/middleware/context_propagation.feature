Feature: Request Context Propagation
  As a developer
  I want request context automatically available in my code
  So that all logs and metrics include request correlation data

  Background:
    Given in-memory log storage
    And in-memory metrics storage
    And an ASGI app with observability middleware

  Scenario: Context is available in endpoint handlers
    Given an endpoint that calls get_log_context()
    When a GET request is made with X-Request-ID="req-123"
    Then the endpoint should see request_id="req-123" in context

  Scenario: Context is available in nested async calls
    Given an endpoint that awaits a service that awaits a repository
    And each layer writes a log entry
    When a request is made
    Then all 3 log entries should have the same request_id

  Scenario: Context is isolated between concurrent requests
    When 10 concurrent requests are made with unique request IDs
    Then each request's logs should only contain its own request_id
    And no cross-contamination should occur

  Scenario: Context is cleared after request completes
    When a request is made with request_id="req-abc"
    And then another request is made without X-Request-ID
    Then the second request should have a different request_id
    And the second request should not see "req-abc"

  Scenario: Custom context attributes can be added during request
    Given an endpoint that calls update_log_context(user_id="u456")
    When a request is made
    Then subsequent logs in that request should have user_id="u456"
    But the next request should not have user_id
