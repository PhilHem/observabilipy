"""Registry for event-to-observability mapping functions."""

from collections.abc import Callable, Iterable
from typing import Any

from observabilipy.core.models import LogEntry, MetricSample

# Type alias for mapper functions
MapperFunc = Callable[[Any], Iterable[LogEntry | MetricSample]]


class MappingRegistry:
    """Registry for event-to-observability mapping functions.

    Stores callable functions that convert domain events into
    observability outputs (LogEntry and MetricSample).

    Example:
        >>> registry = MappingRegistry()
        >>> def order_mapper(event):
        ...     return [LogEntry(timestamp=1.0, level="INFO", message="Order placed")]
        >>> registry.register("OrderPlaced", order_mapper)
        >>> mapper = registry.lookup("OrderPlaced")
        >>> mapper is order_mapper
        True
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._mappings: dict[str, MapperFunc] = {}

    def register(self, event_class: str, mapper: MapperFunc) -> None:
        """Register a mapping function for an event type.

        Args:
            event_class: Name of the domain event class.
            mapper: Callable that takes an event and returns an iterable
                   of LogEntry and/or MetricSample objects.

        Raises:
            TypeError: If mapper is not callable.
            ValueError: If a mapping for event_class already exists.

        Example:
            >>> registry = MappingRegistry()
            >>> def mapper(event): return []
            >>> registry.register("MyEvent", mapper)
        """
        if not callable(mapper):
            raise TypeError(f"mapper must be callable, got {type(mapper).__name__}")
        if event_class in self._mappings:
            raise ValueError(f"mapping for '{event_class}' already registered")
        self._mappings[event_class] = mapper

    def lookup(self, event_class: str) -> MapperFunc | None:
        """Look up the mapper for an event type.

        Args:
            event_class: Name of the domain event class.

        Returns:
            The registered mapper function, or None if not found.

        Example:
            >>> registry = MappingRegistry()
            >>> registry.lookup("UnknownEvent") is None
            True
        """
        return self._mappings.get(event_class)

    def validate_mappings(self, test_events: dict[str, Any] | None = None) -> list[str]:
        """Validate all registered mappings.

        Optionally tests mappers with sample events to verify their output
        types are correct (LogEntry or MetricSample).

        Args:
            test_events: Optional mapping of event_class to test event instances.
                        If provided, mappers are invoked with these events
                        and their outputs are validated.

        Returns:
            List of error messages. Empty list means all validations passed.

        Example:
            >>> registry = MappingRegistry()
            >>> def bad_mapper(event): return ["not valid"]
            >>> registry.register("BadEvent", bad_mapper)
            >>> errors = registry.validate_mappings(test_events={"BadEvent": object()})
            >>> len(errors) > 0
            True
        """
        errors: list[str] = []

        if test_events is None:
            return errors

        for event_class, test_event in test_events.items():
            mapper = self._mappings.get(event_class)
            if mapper is None:
                continue

            try:
                outputs = mapper(test_event)
                for output in outputs:
                    if not isinstance(output, (LogEntry, MetricSample)):
                        errors.append(
                            f"'{event_class}' mapper returned invalid output "
                            f"type: {type(output).__name__}. "
                            f"Expected LogEntry or MetricSample."
                        )
            except Exception as e:
                errors.append(f"'{event_class}' mapper raised exception: {e}")

        return errors

    def __len__(self) -> int:
        """Return the number of registered mappings.

        Example:
            >>> registry = MappingRegistry()
            >>> len(registry)
            0
            >>> registry.register("Event1", lambda e: [])
            >>> len(registry)
            1
        """
        return len(self._mappings)

    def merge(self, other: "MappingRegistry") -> None:
        """Merge all mappings from another registry into this one.

        Copies all mappings from the source registry. The source registry
        is not modified.

        Args:
            other: Registry to copy mappings from.

        Raises:
            ValueError: If any event names conflict with existing mappings.

        Example:
            >>> registry1 = MappingRegistry()
            >>> registry1.register("Event1", lambda e: [])
            >>> registry2 = MappingRegistry()
            >>> registry2.register("Event2", lambda e: [])
            >>> registry1.merge(registry2)
            >>> len(registry1)
            2
        """
        conflicts = set(self._mappings.keys()) & set(other._mappings.keys())
        if conflicts:
            raise ValueError(f"duplicate event names: {', '.join(sorted(conflicts))}")
        self._mappings.update(other._mappings)
