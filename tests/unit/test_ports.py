"""Tests for port interfaces."""

from collections.abc import AsyncGenerator

import pytest

from observabilipy.core.models import LogEntry, MetricSample
from observabilipy.core.ports import LogStoragePort, MetricsStoragePort


class TestLogStoragePort:
    """Tests for LogStoragePort protocol."""

    @pytest.mark.core
    def test_protocol_has_write_method(self) -> None:
        """LogStoragePort must define write(entry: LogEntry) -> None."""
        assert hasattr(LogStoragePort, "write")

    @pytest.mark.core
    def test_protocol_has_read_method(self) -> None:
        """LogStoragePort must define read(since: float) -> AsyncIterable[LogEntry]."""
        assert hasattr(LogStoragePort, "read")

    @pytest.mark.core
    def test_class_implementing_protocol_is_recognized(self) -> None:
        """A class with all required methods should satisfy LogStoragePort."""

        class FakeLogStorage:
            async def write(self, entry: LogEntry) -> None:
                pass

            async def read(self, since: float = 0) -> AsyncGenerator[LogEntry]:
                return
                yield  # Make this an async generator

            async def count(self) -> int:
                return 0

            async def delete_before(self, timestamp: float) -> int:
                return 0

            async def delete_by_level_before(self, level: str, timestamp: float) -> int:
                return 0

            async def count_by_level(self, level: str) -> int:
                return 0

        storage: LogStoragePort = FakeLogStorage()
        assert isinstance(storage, LogStoragePort)


class TestMetricsStoragePort:
    """Tests for MetricsStoragePort protocol."""

    @pytest.mark.core
    def test_protocol_has_write_method(self) -> None:
        """MetricsStoragePort must define write(sample: MetricSample) -> None."""
        assert hasattr(MetricsStoragePort, "write")

    @pytest.mark.core
    def test_protocol_has_read_method(self) -> None:
        """MetricsStoragePort must define read(since) -> AsyncIterable."""
        assert hasattr(MetricsStoragePort, "read")

    @pytest.mark.core
    def test_class_implementing_protocol_is_recognized(self) -> None:
        """A class with all required methods should satisfy MetricsStoragePort."""

        class FakeMetricsStorage:
            async def write(self, sample: MetricSample) -> None:
                pass

            async def read(self, since: float = 0) -> AsyncGenerator[MetricSample]:
                return
                yield  # Make this an async generator

            async def count(self) -> int:
                return 0

            async def delete_before(self, timestamp: float) -> int:
                return 0

        storage: MetricsStoragePort = FakeMetricsStorage()
        assert isinstance(storage, MetricsStoragePort)
