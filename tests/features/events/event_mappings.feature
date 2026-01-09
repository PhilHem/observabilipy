Feature: Event Mapping Functions
  As a library user
  I want to register functions that convert domain events to observability outputs
  So that I control exactly how events become metrics and logs

  Scenario: Register a mapping function for an event type
    Given a domain event class "OrderPlaced"
    And a mapping function that returns a log entry and a counter
    When I register the mapping for "OrderPlaced"
    Then the registry should contain a mapping for "OrderPlaced"

  Scenario: Mapping function receives the event instance
    Given a domain event "OrderPlaced" with order_id="ORD-123" and amount=99.99
    And a mapping function that extracts these attributes
    When I record the event
    Then the mapping function should receive the event instance
    And the log entry should contain order_id="ORD-123"

  Scenario: Mapping function returns multiple outputs
    Given a mapping function that returns:
      | type      | name                 |
      | log       | Order placed         |
      | counter   | orders_total         |
      | histogram | order_amount_dollars |
    When I record an "OrderPlaced" event
    Then all 3 outputs should be written to storage
