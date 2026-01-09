Feature: Event Recording
  As a library user
  I want to record domain events and have them converted to metrics and logs
  So that I don't need to manually call counter() or info()

  Background:
    Given in-memory metrics storage
    And in-memory log storage
    And a domain event class "UserRegistered" with attributes:
      | attribute | type |
      | user_id   | str  |
      | email     | str  |
    And an EventDescriptor for "UserRegistered" with:
      | type    | name                      | config                 |
      | log     | User registered           | fields: user_id, email |
      | counter | user_registrations_total  | labels: -              |
    And an EventObservability instance with these descriptors

  Scenario: Recording an event produces a log entry
    When I record a "UserRegistered" event with user_id="u123" and email="test@example.com"
    Then the log storage should contain 1 entry
    And the log entry should have message "User registered"
    And the log entry should have attribute "user_id" = "u123"
    And the log entry should have attribute "email" = "test@example.com"

  Scenario: Recording an event produces a counter metric
    When I record a "UserRegistered" event with user_id="u123" and email="test@example.com"
    Then the metrics storage should contain a sample named "user_registrations_total"
    And the sample value should be 1.0

  Scenario: Recording an unknown event is silently ignored
    Given a domain event class "UnknownEvent" with no descriptor
    When I record an "UnknownEvent" instance
    Then the log storage should be empty
    And the metrics storage should be empty

  Scenario: Recording works in sync context (no running event loop)
    Given no running asyncio event loop
    When I record a "UserRegistered" event synchronously
    Then the log storage should contain 1 entry
    And the metrics storage should contain samples
