Feature: Automatic Request Logging
  As a service operator
  I want HTTP requests automatically logged
  So that I have visibility without instrumenting every endpoint

  Background:
    Given in-memory log storage
    And in-memory metrics storage
    And an ASGI app with observability middleware

  Scenario: Successful request is logged with standard attributes
    When a GET request is made to "/users/123"
    And the endpoint returns status 200
    Then a log entry should be recorded with:
      | attribute   | value       |
      | level       | INFO        |
      | method      | GET         |
      | path        | /users/123  |
      | status_code | 200         |
    And the log entry should have a "duration_ms" attribute

  Scenario: Failed request is logged with error level
    When a GET request is made to "/users/999"
    And the endpoint returns status 404
    Then a log entry should be recorded with:
      | attribute   | value |
      | level       | WARN  |
      | status_code | 404   |

  Scenario: Server error is logged with ERROR level
    When a GET request is made to "/explode"
    And the endpoint raises an unhandled exception
    Then a log entry should be recorded with:
      | attribute   | value |
      | level       | ERROR |
      | status_code | 500   |
    And the log entry should have an "exception" attribute

  Scenario: Request ID is generated when not provided
    When a GET request is made without X-Request-ID header
    Then a log entry should be recorded with a "request_id" attribute
    And the request_id should be a valid UUID

  Scenario: Request ID is preserved from incoming header
    When a GET request is made with header X-Request-ID="req-abc-123"
    Then a log entry should be recorded with request_id="req-abc-123"

  Scenario: All logs within request share the same request_id
    Given an endpoint that writes 3 application logs
    When a GET request is made to that endpoint
    Then 4 log entries should be recorded
    And all log entries should have the same request_id
