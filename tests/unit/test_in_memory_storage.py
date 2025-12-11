"""Tests for in-memory storage adapters."""

import pytest

from observability.core.models import LogEntry, MetricSample
from observability.core.ports import LogStoragePort, MetricsStoragePort
from observability.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)


class TestInMemoryLogStorage:
    """Tests for InMemoryLogStorage adapter."""

    @pytest.mark.storage
    def test_implements_log_storage_port(self) -> None:
        """InMemoryLogStorage must satisfy LogStoragePort protocol."""
        storage = InMemoryLogStorage()
        assert isinstance(storage, LogStoragePort)

    @pytest.mark.storage
    def test_write_and_read_single_entry(self) -> None:
        """Can write a log entry and read it back."""
        storage = InMemoryLogStorage()
        entry = LogEntry(timestamp=1000.0, level="INFO", message="test message")

        storage.write(entry)
        result = list(storage.read())

        assert result == [entry]

    @pytest.mark.storage
    def test_read_returns_empty_when_no_entries(self) -> None:
        """Read returns empty iterable when storage is empty."""
        storage = InMemoryLogStorage()

        result = list(storage.read())

        assert result == []

    @pytest.mark.storage
    def test_read_filters_by_since_timestamp(self) -> None:
        """Read only returns entries with timestamp > since."""
        storage = InMemoryLogStorage()
        old_entry = LogEntry(timestamp=1000.0, level="INFO", message="old")
        new_entry = LogEntry(timestamp=2000.0, level="INFO", message="new")

        storage.write(old_entry)
        storage.write(new_entry)
        result = list(storage.read(since=1000.0))

        assert result == [new_entry]

    @pytest.mark.storage
    def test_read_returns_entries_ordered_by_timestamp(self) -> None:
        """Read returns entries ordered by timestamp ascending."""
        storage = InMemoryLogStorage()
        entry_3 = LogEntry(timestamp=3000.0, level="INFO", message="third")
        entry_1 = LogEntry(timestamp=1000.0, level="INFO", message="first")
        entry_2 = LogEntry(timestamp=2000.0, level="INFO", message="second")

        # Write out of order
        storage.write(entry_3)
        storage.write(entry_1)
        storage.write(entry_2)
        result = list(storage.read())

        assert result == [entry_1, entry_2, entry_3]

    @pytest.mark.storage
    def test_write_multiple_entries(self) -> None:
        """Can write multiple entries and read them all back."""
        storage = InMemoryLogStorage()
        entries = [
            LogEntry(timestamp=1000.0 + i, level="INFO", message=f"msg {i}")
            for i in range(5)
        ]

        for entry in entries:
            storage.write(entry)
        result = list(storage.read())

        assert result == entries


class TestInMemoryMetricsStorage:
    """Tests for InMemoryMetricsStorage adapter."""

    @pytest.mark.storage
    def test_implements_metrics_storage_port(self) -> None:
        """InMemoryMetricsStorage must satisfy MetricsStoragePort protocol."""
        storage = InMemoryMetricsStorage()
        assert isinstance(storage, MetricsStoragePort)

    @pytest.mark.storage
    def test_write_and_scrape_single_sample(self) -> None:
        """Can write a metric sample and scrape it back."""
        storage = InMemoryMetricsStorage()
        sample = MetricSample(name="requests_total", timestamp=1000.0, value=42.0)

        storage.write(sample)
        result = list(storage.scrape())

        assert result == [sample]

    @pytest.mark.storage
    def test_scrape_returns_empty_when_no_samples(self) -> None:
        """Scrape returns empty iterable when storage is empty."""
        storage = InMemoryMetricsStorage()

        result = list(storage.scrape())

        assert result == []

    @pytest.mark.storage
    def test_write_multiple_samples(self) -> None:
        """Can write multiple samples and scrape them all back."""
        storage = InMemoryMetricsStorage()
        samples = [
            MetricSample(name=f"metric_{i}", timestamp=1000.0 + i, value=float(i))
            for i in range(5)
        ]

        for sample in samples:
            storage.write(sample)
        result = list(storage.scrape())

        assert result == samples

    @pytest.mark.storage
    def test_samples_with_different_labels_are_distinct(self) -> None:
        """Samples with same name but different labels are stored separately."""
        storage = InMemoryMetricsStorage()
        sample_a = MetricSample(
            name="http_requests",
            timestamp=1000.0,
            value=10.0,
            labels={"method": "GET"},
        )
        sample_b = MetricSample(
            name="http_requests",
            timestamp=1001.0,
            value=5.0,
            labels={"method": "POST"},
        )

        storage.write(sample_a)
        storage.write(sample_b)
        result = list(storage.scrape())

        assert len(result) == 2
        assert sample_a in result
        assert sample_b in result
