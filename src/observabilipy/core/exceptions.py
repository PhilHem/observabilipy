"""Custom exceptions for observability library."""


class ObservabilityError(Exception):
    """Base exception for all observability errors.

    All custom exceptions in this library inherit from this class,
    allowing callers to catch all library-specific errors with a
    single except clause.
    """


class ConfigurationError(ObservabilityError):
    """Raised when configuration values are invalid.

    This exception is raised during initialization when configuration
    parameters fail validation. The error message includes the specific
    field that failed, the constraint violated, and the actual value.

    Example:
        >>> RetentionPolicy(max_age_seconds=-1.0)
        ConfigurationError: max_age_seconds must be positive, got -1.0
    """
