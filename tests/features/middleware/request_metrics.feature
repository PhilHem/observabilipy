Feature: Automatic Request Metrics
  As a service operator
  I want HTTP request metrics automatically recorded
  So that I can monitor traffic patterns and latency

  Background:
    Given in-memory log storage
    And in-memory metrics storage
    And an ASGI app with observability middleware

  Scenario: Request counter incremented on each request
    When 3 GET requests are made to "/health"
    Then the metric "http_requests_total" should have count 3
    And the metric should have labels:
      | label  | value   |
      | method | GET     |
      | path   | /health |
      | status | 200     |

  Scenario: Different status codes have separate counters
    When a GET request returns status 200
    And a GET request returns status 404
    And a GET request returns status 500
    Then "http_requests_total" with status="200" should have count 1
    And "http_requests_total" with status="404" should have count 1
    And "http_requests_total" with status="500" should have count 1

  Scenario: Request duration histogram is recorded
    When a GET request is made that takes 150ms
    Then the metric "http_request_duration_seconds" should be recorded
    And the histogram should have a sample in the 0.1-0.25 bucket

  Scenario: Histogram buckets follow Prometheus conventions
    When a request is made
    Then "http_request_duration_seconds" should have buckets:
      | le    |
      | 0.005 |
      | 0.01  |
      | 0.025 |
      | 0.05  |
      | 0.1   |
      | 0.25  |
      | 0.5   |
      | 1.0   |
      | 2.5   |
      | 5.0   |
      | 10.0  |
      | +Inf  |

  Scenario: Path normalization prevents cardinality explosion
    When requests are made to "/users/1", "/users/2", "/users/3"
    Then the path label should be "/users/{id}" for all requests
    And there should be 1 unique label combination, not 3
