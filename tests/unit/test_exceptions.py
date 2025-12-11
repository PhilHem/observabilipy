"""Tests for custom exceptions."""

import pytest

from observabilipy.core.exceptions import ConfigurationError, ObservabilityError


class TestObservabilityError:
    """Tests for base ObservabilityError."""

    @pytest.mark.core
    def test_base_exception_is_exception_subclass(self) -> None:
        assert issubclass(ObservabilityError, Exception)

    @pytest.mark.core
    def test_base_exception_can_be_raised_and_caught(self) -> None:
        with pytest.raises(ObservabilityError):
            raise ObservabilityError("test error")


class TestConfigurationError:
    """Tests for ConfigurationError."""

    @pytest.mark.core
    def test_configuration_error_is_observability_error(self) -> None:
        assert issubclass(ConfigurationError, ObservabilityError)

    @pytest.mark.core
    def test_configuration_error_preserves_message(self) -> None:
        error = ConfigurationError("max_age_seconds must be positive, got -1.0")
        assert "max_age_seconds" in str(error)
        assert "positive" in str(error)
        assert "-1.0" in str(error)

    @pytest.mark.core
    def test_configuration_error_can_be_caught_as_base(self) -> None:
        with pytest.raises(ObservabilityError):
            raise ConfigurationError("invalid config")
