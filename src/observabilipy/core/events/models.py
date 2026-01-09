"""Event descriptor models for mapping domain events to observability outputs."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class LogTemplate:
    """Template for generating a log entry from a domain event.

    Attributes:
        message: The log message to emit.
        event_type: Event type identifier for log attributes.
        fields: Attribute names to extract from the event into log attributes.

    Example:
        >>> template = LogTemplate(
        ...     message="Order placed",
        ...     event_type="order_placed",
        ...     fields=("order_id", "customer_id"),
        ... )
        >>> template.message
        'Order placed'
        >>> template.fields
        ('order_id', 'customer_id')
    """

    message: str
    event_type: str
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetricTemplate:
    """Template for generating a metric sample from a domain event.

    Attributes:
        name: Metric name (e.g., "orders_total", "request_duration_seconds").
        metric_type: Type of metric - counter, gauge, or histogram.
        labels: Attribute names to extract from the event as metric labels.
        value_field: Attribute name to extract as the metric value.
                    Required for gauge/histogram, ignored for counters.
        buckets: Histogram bucket boundaries. Only used for histogram type.

    Example:
        >>> counter = MetricTemplate(
        ...     name="orders_total",
        ...     metric_type="counter",
        ...     labels=("customer_id",),
        ... )
        >>> counter.name
        'orders_total'

        >>> histogram = MetricTemplate(
        ...     name="order_amount_dollars",
        ...     metric_type="histogram",
        ...     value_field="total_amount",
        ...     buckets=(10.0, 50.0, 100.0, 500.0),
        ... )
        >>> histogram.buckets
        (10.0, 50.0, 100.0, 500.0)
    """

    name: str
    metric_type: Literal["counter", "gauge", "histogram"]
    labels: tuple[str, ...] = ()
    value_field: str | None = None
    buckets: tuple[float, ...] | None = None


@dataclass(frozen=True)
class EventDescriptor:
    """Maps a domain event class to observability outputs.

    An EventDescriptor defines what logs and metrics should be emitted
    when a domain event occurs. This decouples the domain from
    observability concerns.

    Attributes:
        event_class: Name of the domain event class this descriptor handles.
        log_templates: Templates for log entries to emit.
        metric_templates: Templates for metric samples to emit.

    Example:
        >>> log = LogTemplate(
        ...     message="Order placed",
        ...     event_type="order_placed",
        ...     fields=("order_id",),
        ... )
        >>> counter = MetricTemplate(
        ...     name="orders_total",
        ...     metric_type="counter",
        ... )
        >>> descriptor = EventDescriptor(
        ...     event_class="OrderPlaced",
        ...     log_templates=(log,),
        ...     metric_templates=(counter,),
        ... )
        >>> descriptor.event_class
        'OrderPlaced'
        >>> len(descriptor.log_templates)
        1
    """

    event_class: str
    log_templates: tuple[LogTemplate, ...] = field(default_factory=tuple)
    metric_templates: tuple[MetricTemplate, ...] = field(default_factory=tuple)
