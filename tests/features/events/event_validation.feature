Feature: Mapping Registry Validation
  As a library user
  I want to catch configuration errors at startup
  So that I don't discover problems in production

  Scenario: Registering a non-callable raises TypeError
    Given a value that is not callable
    When I try to register it as a mapping
    Then a TypeError should be raised

  Scenario: Duplicate registration for same event type raises ValueError
    Given a mapping already registered for "OrderPlaced"
    When I try to register another mapping for "OrderPlaced"
    Then a ValueError should be raised with message containing "already registered"

  Scenario: Validate all mappings returns errors for invalid mappers
    Given a mapping function that returns invalid output types
    When I call validate_mappings()
    Then validation should return errors describing the invalid outputs
