Feature: Event Recording
  As a library user
  I want to record domain events through a single API
  So that observability is decoupled from my domain code

  Background:
    Given in-memory metrics storage
    And in-memory log storage

  Scenario: Recording an event invokes its registered mapper
    Given a domain event class "UserRegistered" with user_id and email attributes
    And a registered mapping function for "UserRegistered"
    When I record a UserRegistered event with user_id="u123" and email="test@example.com"
    Then the mapping function should be invoked with the event
    And its outputs should be written to storage

  Scenario: Recording an unmapped event is silently ignored
    Given no mapping registered for "UnknownEvent"
    When I record an "UnknownEvent" instance
    Then no error should be raised
    And storage should be empty

  Scenario: Recording works in sync context (no running event loop)
    Given a registered mapping for "UserRegistered"
    And no running asyncio event loop
    When I record a UserRegistered event synchronously
    Then the outputs should be written to storage

  Scenario: Recording works in async context
    Given a registered mapping for "UserRegistered"
    And a running asyncio event loop
    When I record a UserRegistered event asynchronously
    Then the outputs should be written to storage
