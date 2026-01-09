"""BDD step definitions for event observability features."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from observabilipy.adapters.events import EventObservability
from observabilipy.adapters.storage.in_memory import (
    InMemoryLogStorage,
    InMemoryMetricsStorage,
)
from observabilipy.core.events.registry import MappingRegistry
from observabilipy.core.models import LogEntry, MetricSample

# === Domain Event Classes ===


@dataclass
class OrderPlaced:
    """Test domain event for orders."""

    order_id: str = ""
    amount: float = 0.0


@dataclass
class UserRegistered:
    """Test domain event for user registration."""

    user_id: str = ""
    email: str = ""


@dataclass
class UnknownEvent:
    """Test domain event with no mapping registered."""

    data: str = ""


@dataclass
class BadEvent:
    """Test domain event for validation tests."""

    data: str = ""


EVENT_CLASSES: dict[str, type] = {
    "OrderPlaced": OrderPlaced,
    "UserRegistered": UserRegistered,
    "UnknownEvent": UnknownEvent,
    "BadEvent": BadEvent,
}


# === Scenario Context ===


@dataclass
class ScenarioContext:
    """Shared state between steps in a scenario."""

    registry: MappingRegistry = field(default_factory=MappingRegistry)
    log_storage: InMemoryLogStorage = field(default_factory=InMemoryLogStorage)
    metrics_storage: InMemoryMetricsStorage = field(
        default_factory=InMemoryMetricsStorage
    )
    adapter: EventObservability | None = None
    event_class: type | None = None
    event_instance: Any | None = None
    mapper_received_event: Any | None = None
    mapper_func: Any | None = None
    non_callable_value: Any | None = None
    exception: Exception | None = None
    validation_errors: list[str] = field(default_factory=list)
    expected_outputs: list[dict[str, str]] = field(default_factory=list)


@pytest.fixture
def ctx() -> ScenarioContext:
    """Fresh scenario context for each test."""
    return ScenarioContext()


# === Background Steps (event_recording.feature) ===


@given("in-memory metrics storage")
def given_inmemory_metrics_storage(ctx: ScenarioContext) -> None:
    """Initialize in-memory metrics storage."""
    ctx.metrics_storage = InMemoryMetricsStorage()


@given("in-memory log storage")
def given_inmemory_log_storage(ctx: ScenarioContext) -> None:
    """Initialize in-memory log storage."""
    ctx.log_storage = InMemoryLogStorage()


# === Given Steps ===


@given(parsers.parse('a domain event class "{name}"'))
def given_domain_event_class(ctx: ScenarioContext, name: str) -> None:
    """Store reference to a domain event class."""
    ctx.event_class = EVENT_CLASSES.get(name, OrderPlaced)


@given(parsers.parse('a domain event class "{name}" with user_id and email attributes'))
def given_domain_event_class_with_attributes(ctx: ScenarioContext, name: str) -> None:
    """Store reference to UserRegistered event class."""
    ctx.event_class = UserRegistered


@given("a mapping function that returns a log entry and a counter")
def given_mapping_returns_log_and_counter(ctx: ScenarioContext) -> None:
    """Create a mapping function returning log entry and counter metric."""

    def mapper(event: Any) -> list[LogEntry | MetricSample]:
        return [
            LogEntry(timestamp=1.0, level="INFO", message="Event recorded"),
            MetricSample(name="events_total", timestamp=1.0, value=1.0, labels={}),
        ]

    ctx.mapper_func = mapper


@given(
    parsers.parse(
        'a domain event "{name}" with order_id="{order_id}" and amount={amount:g}'
    )
)
def given_domain_event_with_attributes(
    ctx: ScenarioContext, name: str, order_id: str, amount: float
) -> None:
    """Create an event instance with specific attributes."""
    ctx.event_class = OrderPlaced
    ctx.event_instance = OrderPlaced(order_id=order_id, amount=amount)


@given("a mapping function that extracts these attributes")
def given_mapping_extracts_attributes(ctx: ScenarioContext) -> None:
    """Create a mapping function that captures the event and extracts attributes."""

    def mapper(event: OrderPlaced) -> list[LogEntry | MetricSample]:
        ctx.mapper_received_event = event
        return [
            LogEntry(
                timestamp=1.0,
                level="INFO",
                message="Order placed",
                attributes={"order_id": event.order_id, "amount": str(event.amount)},
            ),
        ]

    ctx.mapper_func = mapper
    ctx.registry.register("OrderPlaced", mapper)
    ctx.adapter = EventObservability(ctx.registry, ctx.log_storage, ctx.metrics_storage)


@given("a mapping function that returns:")
def given_mapping_returns_multiple(
    ctx: ScenarioContext, datatable: list[list[str]]
) -> None:
    """Create mapping function returning multiple output types from table."""
    outputs: list[dict[str, str]] = []
    # Skip header row, parse data rows
    for row in datatable[1:]:
        if len(row) >= 2:
            outputs.append({"type": row[0], "name": row[1]})

    ctx.expected_outputs = outputs

    def mapper(event: OrderPlaced) -> list[LogEntry | MetricSample]:
        result: list[LogEntry | MetricSample] = []
        for output in outputs:
            if output["type"] == "log":
                result.append(
                    LogEntry(timestamp=1.0, level="INFO", message=output["name"])
                )
            elif output["type"] == "counter":
                result.append(
                    MetricSample(
                        name=output["name"], timestamp=1.0, value=1.0, labels={}
                    )
                )
            elif output["type"] == "histogram":
                result.append(
                    MetricSample(
                        name=output["name"],
                        timestamp=1.0,
                        value=event.amount,
                        labels={},
                    )
                )
        return result

    ctx.mapper_func = mapper
    ctx.registry.register("OrderPlaced", mapper)
    ctx.adapter = EventObservability(ctx.registry, ctx.log_storage, ctx.metrics_storage)


@given(parsers.parse('a registered mapping function for "{name}"'))
def given_registered_mapping_for(ctx: ScenarioContext, name: str) -> None:
    """Register a mapping function for the named event class."""

    def mapper(event: Any) -> list[LogEntry | MetricSample]:
        ctx.mapper_received_event = event
        return [
            LogEntry(
                timestamp=1.0,
                level="INFO",
                message=f"{name} recorded",
                attributes={
                    "user_id": getattr(event, "user_id", ""),
                    "email": getattr(event, "email", ""),
                },
            ),
            MetricSample(
                name=f"{name.lower()}_total", timestamp=1.0, value=1.0, labels={}
            ),
        ]

    ctx.mapper_func = mapper
    ctx.registry.register(name, mapper)
    ctx.adapter = EventObservability(ctx.registry, ctx.log_storage, ctx.metrics_storage)


@given(parsers.parse('no mapping registered for "{name}"'))
def given_no_mapping_for(ctx: ScenarioContext, name: str) -> None:
    """Ensure no mapping is registered for the event class."""
    ctx.adapter = EventObservability(ctx.registry, ctx.log_storage, ctx.metrics_storage)


@given(parsers.parse('a registered mapping for "{name}"'))
def given_registered_mapping(ctx: ScenarioContext, name: str) -> None:
    """Register a simple mapping function."""

    def mapper(event: Any) -> list[LogEntry]:
        ctx.mapper_received_event = event
        return [LogEntry(timestamp=1.0, level="INFO", message="test")]

    ctx.mapper_func = mapper
    ctx.registry.register(name, mapper)
    ctx.adapter = EventObservability(ctx.registry, ctx.log_storage, ctx.metrics_storage)


@given("no running asyncio event loop")
def given_no_event_loop(ctx: ScenarioContext) -> None:
    """Context for sync execution - no special setup needed."""
    pass  # Sync context is the default in pytest


@given("a running asyncio event loop")
def given_running_event_loop(ctx: ScenarioContext) -> None:
    """Context for async execution - no special setup needed."""
    pass  # The When step handles async execution


@given("a value that is not callable")
def given_non_callable(ctx: ScenarioContext) -> None:
    """Store a non-callable value."""
    ctx.non_callable_value = "not a callable"


@given(parsers.parse('a mapping already registered for "{name}"'))
def given_mapping_already_registered(ctx: ScenarioContext, name: str) -> None:
    """Register an initial mapping for the event class."""

    def mapper(event: Any) -> list[LogEntry]:
        return []

    ctx.registry.register(name, mapper)


@given("a mapping function that returns invalid output types")
def given_invalid_mapper(ctx: ScenarioContext) -> None:
    """Register a mapping function that returns invalid output types."""

    def bad_mapper(event: Any) -> list[str]:
        return ["invalid output"]

    ctx.mapper_func = bad_mapper
    ctx.registry.register("BadEvent", bad_mapper)  # type: ignore[arg-type]


# === When Steps ===


@when(parsers.parse('I register the mapping for "{name}"'))
def when_register_mapping(ctx: ScenarioContext, name: str) -> None:
    """Register the mapping function for the event class."""
    if ctx.mapper_func:
        ctx.registry.register(name, ctx.mapper_func)


@when("I record the event")
def when_record_event(ctx: ScenarioContext) -> None:
    """Record the event instance through the adapter."""
    if ctx.event_instance and ctx.adapter:
        asyncio.run(ctx.adapter.record_async(ctx.event_instance))


@when(parsers.parse('I record an "{name}" event'))
def when_record_named_event(ctx: ScenarioContext, name: str) -> None:
    """Create and record an event of the named class."""
    event_class = EVENT_CLASSES.get(name, OrderPlaced)
    if name == "OrderPlaced":
        ctx.event_instance = OrderPlaced(order_id="ORD-001", amount=50.0)
    else:
        ctx.event_instance = event_class()

    if ctx.adapter:
        asyncio.run(ctx.adapter.record_async(ctx.event_instance))


@when(
    parsers.parse(
        'I record a UserRegistered event with user_id="{user_id}" and email="{email}"'
    )
)
def when_record_user_registered(ctx: ScenarioContext, user_id: str, email: str) -> None:
    """Create and record a UserRegistered event."""
    ctx.event_instance = UserRegistered(user_id=user_id, email=email)
    if ctx.adapter:
        asyncio.run(ctx.adapter.record_async(ctx.event_instance))


@when(parsers.parse('I record an "{name}" instance'))
def when_record_instance(ctx: ScenarioContext, name: str) -> None:
    """Create and record an event instance."""
    event_class = EVENT_CLASSES.get(name, UnknownEvent)
    ctx.event_instance = event_class()
    if ctx.adapter:
        asyncio.run(ctx.adapter.record_async(ctx.event_instance))


@when("I record a UserRegistered event synchronously")
def when_record_sync(ctx: ScenarioContext) -> None:
    """Record event using sync API."""
    ctx.event_instance = UserRegistered(user_id="sync-user", email="sync@test.com")
    if ctx.adapter:
        ctx.adapter.record(ctx.event_instance)


@when("I record a UserRegistered event asynchronously")
def when_record_async(ctx: ScenarioContext) -> None:
    """Record event using async API."""
    ctx.event_instance = UserRegistered(user_id="async-user", email="async@test.com")

    async def do_record() -> None:
        if ctx.adapter:
            await ctx.adapter.record_async(ctx.event_instance)

    asyncio.run(do_record())


@when("I try to register it as a mapping")
def when_try_register_non_callable(ctx: ScenarioContext) -> None:
    """Attempt to register a non-callable as a mapping."""
    try:
        ctx.registry.register("TestEvent", ctx.non_callable_value)  # type: ignore[arg-type]
    except TypeError as e:
        ctx.exception = e


@when(parsers.parse('I try to register another mapping for "{name}"'))
def when_try_duplicate_register(ctx: ScenarioContext, name: str) -> None:
    """Attempt to register a second mapping for the same event class."""
    try:

        def mapper2(event: Any) -> list[LogEntry]:
            return []

        ctx.registry.register(name, mapper2)
    except ValueError as e:
        ctx.exception = e


@when("I call validate_mappings()")
def when_call_validate(ctx: ScenarioContext) -> None:
    """Call validate_mappings on the registry."""
    ctx.validation_errors = ctx.registry.validate_mappings(
        test_events={"BadEvent": BadEvent()}
    )


# === Then Steps ===


@then(parsers.parse('the registry should contain a mapping for "{name}"'))
def then_registry_contains_mapping(ctx: ScenarioContext, name: str) -> None:
    """Assert the registry has a mapping for the event class."""
    assert ctx.registry.lookup(name) is not None


@then("the mapping function should receive the event instance")
def then_mapper_received_event(ctx: ScenarioContext) -> None:
    """Assert the mapper received the event."""
    assert ctx.mapper_received_event is not None
    assert ctx.mapper_received_event is ctx.event_instance


@then(parsers.parse('the log entry should contain order_id="{order_id}"'))
def then_log_contains_order_id(ctx: ScenarioContext, order_id: str) -> None:
    """Assert log entry contains the expected order_id attribute."""
    logs = asyncio.run(_read_logs(ctx.log_storage))
    assert len(logs) > 0
    assert logs[0].attributes.get("order_id") == order_id


@then(parsers.parse("all {count:d} outputs should be written to storage"))
def then_all_outputs_written(ctx: ScenarioContext, count: int) -> None:
    """Assert the expected number of outputs were written."""
    log_count = asyncio.run(ctx.log_storage.count())
    metric_count = asyncio.run(ctx.metrics_storage.count())
    total = log_count + metric_count
    assert total == count, (
        f"Expected {count} outputs, got {total} "
        f"(logs={log_count}, metrics={metric_count})"
    )


@then("the mapping function should be invoked with the event")
def then_mapper_invoked(ctx: ScenarioContext) -> None:
    """Assert the mapper was invoked with the event."""
    assert ctx.mapper_received_event is not None


@then("its outputs should be written to storage")
def then_outputs_written(ctx: ScenarioContext) -> None:
    """Assert outputs were written to storage."""
    log_count = asyncio.run(ctx.log_storage.count())
    metric_count = asyncio.run(ctx.metrics_storage.count())
    assert log_count > 0 or metric_count > 0, "No outputs written to storage"


@then("no error should be raised")
def then_no_error(ctx: ScenarioContext) -> None:
    """Assert no exception was raised."""
    assert ctx.exception is None


@then("storage should be empty")
def then_storage_empty(ctx: ScenarioContext) -> None:
    """Assert both storages are empty."""
    log_count = asyncio.run(ctx.log_storage.count())
    metric_count = asyncio.run(ctx.metrics_storage.count())
    assert log_count == 0, f"Expected 0 logs, got {log_count}"
    assert metric_count == 0, f"Expected 0 metrics, got {metric_count}"


@then("the outputs should be written to storage")
def then_outputs_to_storage(ctx: ScenarioContext) -> None:
    """Assert outputs were written to storage."""
    log_count = asyncio.run(ctx.log_storage.count())
    assert log_count > 0, "No logs written to storage"


@then("a TypeError should be raised")
def then_typeerror_raised(ctx: ScenarioContext) -> None:
    """Assert TypeError was raised."""
    assert isinstance(ctx.exception, TypeError)


@then(parsers.parse('a ValueError should be raised with message containing "{text}"'))
def then_valueerror_with_message(ctx: ScenarioContext, text: str) -> None:
    """Assert ValueError was raised with expected message."""
    assert isinstance(ctx.exception, ValueError)
    assert text in str(ctx.exception)


@then("validation should return errors describing the invalid outputs")
def then_validation_errors(ctx: ScenarioContext) -> None:
    """Assert validation returned errors."""
    assert len(ctx.validation_errors) > 0, "Expected validation errors"


# === Helpers ===


async def _read_logs(storage: InMemoryLogStorage) -> list[LogEntry]:
    """Read all logs from storage."""
    return [entry async for entry in storage.read()]
