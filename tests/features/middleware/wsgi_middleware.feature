Feature: WSGI Middleware for Sync Frameworks
  As a Flask/Django-WSGI developer
  I want the same auto-instrumentation as ASGI apps
  So that sync frameworks get equal observability

  Background:
    Given in-memory log storage
    And in-memory metrics storage
    And a WSGI app with observability middleware

  Scenario: WSGI requests are logged
    When a GET request is made to "/api/items"
    Then a log entry should be recorded with method="GET" and path="/api/items"

  Scenario: WSGI metrics are recorded
    When a GET request returns status 200
    Then "http_requests_total" should be incremented with status="200"

  Scenario: WSGI context propagation works
    Given a Flask endpoint that writes an application log
    When a request is made with X-Request-ID="flask-123"
    Then both the middleware log and application log should have request_id="flask-123"

  Scenario: WSGI handles sync storage adapters
    Given sync-only storage adapters
    When a request is made
    Then logs and metrics should be written without async errors

  Scenario: WSGI middleware works with threaded servers
    Given a threaded WSGI server with 4 worker threads
    When concurrent requests hit different threads
    Then each thread should correctly isolate request context
