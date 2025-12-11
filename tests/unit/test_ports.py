"""Tests for port interfaces."""

from collections.abc import Iterable

import pytest

from observability.core.models import LogEntry, MetricSample
from observability.core.ports import LogStoragePort, MetricsStoragePort


class TestLogStoragePort:
    """Tests for LogStoragePort protocol."""

    @pytest.mark.core
    def test_protocol_has_write_method(self) -> None:
        """LogStoragePort must define write(entry: LogEntry) -> None."""
        assert hasattr(LogStoragePort, "write")

    @pytest.mark.core
    def test_protocol_has_read_method(self) -> None:
        """LogStoragePort must define read(since: float) -> Iterable[LogEntry]."""
        assert hasattr(LogStoragePort, "read")

    @pytest.mark.core
    def test_class_implementing_protocol_is_recognized(self) -> None:
        """A class with write and read methods should satisfy LogStoragePort."""

        class FakeLogStorage:
            def write(self, entry: LogEntry) -> None:
                pass

            def read(self, since: float = 0) -> Iterable[LogEntry]:
                return []

        storage: LogStoragePort = FakeLogStorage()
        assert isinstance(storage, LogStoragePort)


class TestMetricsStoragePort:
    """Tests for MetricsStoragePort protocol."""

    @pytest.mark.core
    def test_protocol_has_write_method(self) -> None:
        """MetricsStoragePort must define write(sample: MetricSample) -> None."""
        assert hasattr(MetricsStoragePort, "write")

    @pytest.mark.core
    def test_protocol_has_scrape_method(self) -> None:
        """MetricsStoragePort must define scrape() -> Iterable[MetricSample]."""
        assert hasattr(MetricsStoragePort, "scrape")

    @pytest.mark.core
    def test_class_implementing_protocol_is_recognized(self) -> None:
        """A class with write and scrape methods should satisfy MetricsStoragePort."""

        class FakeMetricsStorage:
            def write(self, sample: MetricSample) -> None:
                pass

            def scrape(self) -> Iterable[MetricSample]:
                return []

        storage: MetricsStoragePort = FakeMetricsStorage()
        assert isinstance(storage, MetricsStoragePort)
