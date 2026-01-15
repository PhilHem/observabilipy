Feature: Middleware Configuration
  As a developer
  I want to configure what the middleware captures
  So that I can balance observability with privacy and performance

  Background:
    Given in-memory log storage
    And in-memory metrics storage

  Scenario: Exclude paths from instrumentation
    Given middleware configured with exclude_paths=["/health", "/metrics"]
    When a GET request is made to "/health"
    Then no log entry should be recorded
    And no metrics should be recorded

  Scenario: Exclude paths supports wildcards
    Given middleware configured with exclude_paths=["/internal/*"]
    When requests are made to "/internal/debug" and "/internal/status"
    Then no log entries should be recorded
    But a request to "/api/users" should be logged

  Scenario: Custom request ID header name
    Given middleware configured with request_id_header="X-Correlation-ID"
    When a request is made with header X-Correlation-ID="corr-999"
    Then the log entry should have request_id="corr-999"

  Scenario: Disable request logging but keep metrics
    Given middleware configured with log_requests=False
    When a GET request is made to "/users"
    Then no log entries should be recorded
    But "http_requests_total" should be incremented

  Scenario: Disable metrics but keep logging
    Given middleware configured with record_metrics=False
    When a GET request is made to "/users"
    Then a log entry should be recorded
    But no metrics should be recorded

  Scenario: Custom metric names
    Given middleware configured with:
      | option                 | value               |
      | request_counter_name   | api_requests_total  |
      | request_histogram_name | api_latency_seconds |
    When a request is made
    Then "api_requests_total" should be incremented
    And "api_latency_seconds" should be recorded
