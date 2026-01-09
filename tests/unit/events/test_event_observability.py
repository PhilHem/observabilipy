"""Unit tests for EventObservability adapter."""

import asyncio
from dataclasses import dataclass

import pytest

from observabilipy.adapters.events import EventObservability
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.events.registry import MappingRegistry
from observabilipy.core.models import LogEntry, MetricSample


@dataclass
class UserRegistered:
    """Test domain event."""

    user_id: str
    email: str


@dataclass
class OrderPlaced:
    """Test domain event with amount."""

    order_id: str
    amount: float


@dataclass
class UnknownEvent:
    """Event with no registered mapping."""

    data: str


class TestEventObservabilityRecord:
    """Tests for EventObservability.record()."""

    @pytest.mark.tra("Events.EventObservability.Record")
    @pytest.mark.tier(0)
    @pytest.mark.asyncio
    async def test_record_invokes_mapper_writes_to_storage(self) -> None:
        """Recording an event invokes its mapper and writes outputs to storage."""
        registry = MappingRegistry()
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        def user_mapper(event: UserRegistered) -> list[LogEntry | MetricSample]:
            return [
                LogEntry(
                    timestamp=1.0,
                    level="INFO",
                    message="User registered",
                    attributes={"user_id": event.user_id, "email": event.email},
                ),
                MetricSample(
                    name="users_registered_total",
                    timestamp=1.0,
                    value=1.0,
                    labels={"user_id": event.user_id},
                ),
            ]

        registry.register("UserRegistered", user_mapper)
        adapter = EventObservability(registry, log_storage, metrics_storage)

        event = UserRegistered(user_id="u123", email="test@example.com")
        await adapter.record_async(event)

        log_count = await log_storage.count()
        metric_count = await metrics_storage.count()
        assert log_count == 1
        assert metric_count == 1

    @pytest.mark.tra("Events.EventObservability.Record.Unmapped")
    @pytest.mark.tier(0)
    @pytest.mark.asyncio
    async def test_record_unmapped_event_silently_ignored(self) -> None:
        """Recording an unmapped event does not raise and writes nothing."""
        registry = MappingRegistry()
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        adapter = EventObservability(registry, log_storage, metrics_storage)

        event = UnknownEvent(data="ignored")
        await adapter.record_async(event)  # Should not raise

        log_count = await log_storage.count()
        metric_count = await metrics_storage.count()
        assert log_count == 0
        assert metric_count == 0


class TestEventObservabilitySyncAsync:
    """Tests for sync/async context handling."""

    @pytest.mark.tra("Events.EventObservability.SyncContext")
    @pytest.mark.tier(0)
    def test_record_sync_context(self) -> None:
        """Recording works in sync context (no running event loop)."""
        registry = MappingRegistry()
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        def mapper(event: UserRegistered) -> list[LogEntry]:
            return [LogEntry(timestamp=1.0, level="INFO", message="test")]

        registry.register("UserRegistered", mapper)
        adapter = EventObservability(registry, log_storage, metrics_storage)

        event = UserRegistered(user_id="u123", email="test@example.com")
        adapter.record(event)  # Sync call, no running event loop

        # Verify write happened
        count = asyncio.run(log_storage.count())
        assert count == 1

    @pytest.mark.tra("Events.EventObservability.AsyncContext")
    @pytest.mark.tier(0)
    @pytest.mark.asyncio
    async def test_record_async_context(self) -> None:
        """Recording works in async context (running event loop)."""
        registry = MappingRegistry()
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        def mapper(event: UserRegistered) -> list[LogEntry]:
            return [LogEntry(timestamp=1.0, level="INFO", message="test")]

        registry.register("UserRegistered", mapper)
        adapter = EventObservability(registry, log_storage, metrics_storage)

        event = UserRegistered(user_id="u123", email="test@example.com")
        adapter.record(event)  # Inside async context

        # Give the scheduled task time to complete
        await asyncio.sleep(0.01)

        count = await log_storage.count()
        assert count == 1


class TestEventObservabilityMultipleOutputs:
    """Tests for handling multiple outputs from mappers."""

    @pytest.mark.tra("Events.EventObservability.MultipleOutputs")
    @pytest.mark.tier(0)
    @pytest.mark.asyncio
    async def test_record_multiple_outputs(self) -> None:
        """Mapper returning multiple outputs writes all to storage."""
        registry = MappingRegistry()
        log_storage = InMemoryLogStorage()
        metrics_storage = InMemoryMetricsStorage()

        def order_mapper(event: OrderPlaced) -> list[LogEntry | MetricSample]:
            return [
                LogEntry(timestamp=1.0, level="INFO", message="Order placed"),
                MetricSample(
                    name="orders_total",
                    timestamp=1.0,
                    value=1.0,
                    labels={},
                ),
                MetricSample(
                    name="order_amount_dollars",
                    timestamp=1.0,
                    value=event.amount,
                    labels={"order_id": event.order_id},
                ),
            ]

        registry.register("OrderPlaced", order_mapper)
        adapter = EventObservability(registry, log_storage, metrics_storage)

        event = OrderPlaced(order_id="ORD-123", amount=99.99)
        await adapter.record_async(event)

        log_count = await log_storage.count()
        metric_count = await metrics_storage.count()
        assert log_count == 1
        assert metric_count == 2
