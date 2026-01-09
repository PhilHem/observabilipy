"""Unit tests for MappingRegistry."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from observabilipy.core.events.registry import MappingRegistry
from observabilipy.core.models import LogEntry


class TestMappingRegistryRegister:
    """Tests for MappingRegistry.register()."""

    @pytest.mark.tra("Events.MappingRegistry.Register")
    @pytest.mark.tier(0)
    def test_register_callable_mapper(self) -> None:
        """Register accepts callable mapping functions."""
        registry = MappingRegistry()

        def mapper(event: object) -> list[LogEntry]:
            return []

        registry.register("OrderPlaced", mapper)

        # Should not raise - registration successful
        assert registry.lookup("OrderPlaced") is mapper

    @pytest.mark.tra("Events.MappingRegistry.Register.NonCallable")
    @pytest.mark.tier(0)
    def test_register_non_callable_raises_typeerror(self) -> None:
        """Register raises TypeError for non-callable values."""
        registry = MappingRegistry()

        with pytest.raises(TypeError, match="mapper must be callable"):
            registry.register("OrderPlaced", "not a callable")  # type: ignore[arg-type]

    @pytest.mark.tra("Events.MappingRegistry.Register.Duplicate")
    @pytest.mark.tier(0)
    def test_duplicate_registration_raises_valueerror(self) -> None:
        """Register raises ValueError for duplicate event class."""
        registry = MappingRegistry()

        def mapper1(event: object) -> list[LogEntry]:
            return []

        def mapper2(event: object) -> list[LogEntry]:
            return []

        registry.register("OrderPlaced", mapper1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("OrderPlaced", mapper2)


class TestMappingRegistryLookup:
    """Tests for MappingRegistry.lookup()."""

    @pytest.mark.tra("Events.MappingRegistry.Lookup")
    @pytest.mark.tier(0)
    def test_lookup_returns_registered_mapper(self) -> None:
        """Lookup returns the registered mapper for an event class."""
        registry = MappingRegistry()

        def mapper(event: object) -> list[LogEntry]:
            return []

        registry.register("OrderPlaced", mapper)

        result = registry.lookup("OrderPlaced")
        assert result is mapper

    @pytest.mark.tra("Events.MappingRegistry.Lookup.NotFound")
    @pytest.mark.tier(0)
    def test_lookup_returns_none_for_unregistered(self) -> None:
        """Lookup returns None for unregistered event classes."""
        registry = MappingRegistry()

        result = registry.lookup("UnknownEvent")
        assert result is None


class TestMappingRegistryValidation:
    """Tests for MappingRegistry.validate_mappings()."""

    @pytest.mark.tra("Events.MappingRegistry.Validate.InvalidOutput")
    @pytest.mark.tier(0)
    def test_validate_mappings_catches_invalid_output(self) -> None:
        """validate_mappings returns errors for mappers with invalid outputs."""
        registry = MappingRegistry()

        def bad_mapper(
            event: object,
        ) -> list[str]:  # Returns strings, not LogEntry/MetricSample
            return ["invalid output"]

        registry.register("BadEvent", bad_mapper)  # type: ignore[arg-type]

        errors = registry.validate_mappings(test_events={"BadEvent": object()})
        assert len(errors) > 0
        assert "BadEvent" in errors[0]

    @pytest.mark.tra("Events.MappingRegistry.Validate.ValidMappers")
    @pytest.mark.tier(0)
    def test_validate_mappings_returns_empty_for_valid_mappers(self) -> None:
        """validate_mappings returns empty list for valid mappers."""
        registry = MappingRegistry()

        def good_mapper(event: object) -> list[LogEntry]:
            return [LogEntry(timestamp=1.0, level="INFO", message="test")]

        registry.register("GoodEvent", good_mapper)

        errors = registry.validate_mappings(test_events={"GoodEvent": object()})
        assert errors == []


class TestMappingRegistryPropertyBased:
    """Property-based tests for MappingRegistry."""

    @pytest.mark.tra("Events.MappingRegistry.Property.Roundtrip")
    @pytest.mark.tier(0)
    @given(event_class=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
    def test_register_lookup_roundtrip(self, event_class: str) -> None:
        """Any non-empty event class can be registered and looked up."""
        registry = MappingRegistry()

        def mapper(event: object) -> list[LogEntry]:
            return []

        registry.register(event_class, mapper)
        result = registry.lookup(event_class)

        assert result is mapper
