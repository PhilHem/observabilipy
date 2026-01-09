Feature: Event Descriptors
  As a library user
  I want to define how domain events map to metrics and logs
  So that I can decouple my domain from observability concerns

  Background:
    Given a domain event class "OrderPlaced" with attributes:
      | attribute    | type  |
      | order_id     | str   |
      | customer_id  | str   |
      | total_amount | float |

  Scenario: Define a log template for an event
    Given a log template with message "Order placed" and event_type "order_placed"
    And the log template extracts fields "order_id, customer_id, total_amount"
    When I create an EventDescriptor for "OrderPlaced" with this log template
    Then the descriptor should have 1 log template
    And the log template fields should be ["order_id", "customer_id", "total_amount"]

  Scenario: Define a counter metric for an event
    Given a metric template of type "counter" named "orders_total"
    And the metric template uses "customer_id" as a label
    When I create an EventDescriptor for "OrderPlaced" with this metric template
    Then the descriptor should have 1 metric template
    And the metric template should be a counter

  Scenario: Define a histogram metric with value extraction
    Given a metric template of type "histogram" named "order_amount_dollars"
    And the metric template extracts value from "total_amount"
    And the metric template has buckets [10, 50, 100, 500, 1000]
    When I create an EventDescriptor for "OrderPlaced" with this metric template
    Then the descriptor should have 1 metric template with buckets

  Scenario: Define multiple outputs for a single event
    Given a log template with message "Order placed" and event_type "order_placed"
    And a metric template of type "counter" named "orders_total"
    And a metric template of type "histogram" named "order_amount_dollars"
    When I create an EventDescriptor with all templates
    Then the descriptor should have 1 log template and 2 metric templates
