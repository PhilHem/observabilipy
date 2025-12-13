"""Tests for observabilipy module docstring documentation."""

import pytest

pytestmark = pytest.mark.core


class TestModuleDocstring:
    """Tests that __init__.py docstring provides quickstart guidance."""

    def test_has_quickstart_section(self) -> None:
        """Docstring has a Quickstart section."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        assert "quickstart" in docstring.lower()

    def test_shows_storage_adapter_usage(self) -> None:
        """Docstring shows how to create a storage adapter."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        assert "InMemoryLogStorage" in docstring

    def test_shows_log_helper_usage(self) -> None:
        """Docstring shows how to use log() helper."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        assert "log(" in docstring or 'log("' in docstring

    def test_shows_counter_helper_usage(self) -> None:
        """Docstring shows how to use counter() helper."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        assert "counter(" in docstring

    def test_shows_embedded_runtime(self) -> None:
        """Docstring shows EmbeddedRuntime for wiring."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        assert "EmbeddedRuntime" in docstring

    def test_shows_framework_integration_path(self) -> None:
        """Docstring shows how to integrate with FastAPI."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        assert "create_observability_router" in docstring

    def test_demonstrates_hexagonal_layers(self) -> None:
        """Docstring mentions the layered architecture."""
        import observabilipy

        docstring = observabilipy.__doc__ or ""
        # Should mention storage as injectable dependency
        assert "storage" in docstring.lower()
