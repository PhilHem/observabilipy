Feature: Event Descriptor Validation
  As a library user
  I want invalid descriptors to fail fast at startup
  So that I catch configuration errors before production

  Scenario: Validation fails for missing log field
    Given a domain event class "SimpleEvent" with attributes:
      | attribute | type |
      | id        | str  |
    And a log template that references field "missing_field"
    When I validate the EventDescriptor
    Then validation should fail with error containing "missing_field"

  Scenario: Validation fails for missing metric label
    Given a domain event class "SimpleEvent" with attributes:
      | attribute | type |
      | id        | str  |
    And a counter metric template with label "nonexistent_attr"
    When I validate the EventDescriptor
    Then validation should fail with error containing "nonexistent_attr"

  Scenario: Validation fails for histogram without value_field
    Given a histogram metric template without value_field
    When I validate the EventDescriptor
    Then validation should fail with error containing "value_field"

  Scenario: Validation passes for valid descriptor
    Given a domain event class "ValidEvent" with attributes:
      | attribute | type  |
      | id        | str   |
      | amount    | float |
    And a log template that references field "id"
    And a histogram metric template with value_field "amount"
    When I validate the EventDescriptor
    Then validation should pass with no errors
