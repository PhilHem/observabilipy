"""Unit tests for event descriptor models."""

import pytest

from observabilipy.core.events import EventDescriptor, LogTemplate, MetricTemplate


class TestLogTemplate:
    """Tests for LogTemplate dataclass."""

    @pytest.mark.tra("Events.LogTemplate.Creation")
    @pytest.mark.tier(0)
    def test_creation_with_required_fields(self) -> None:
        """LogTemplate stores message, event_type, and fields."""
        template = LogTemplate(
            message="Order placed",
            event_type="order_placed",
            fields=("order_id", "customer_id"),
        )

        assert template.message == "Order placed"
        assert template.event_type == "order_placed"
        assert template.fields == ("order_id", "customer_id")

    @pytest.mark.tra("Events.LogTemplate.Defaults")
    @pytest.mark.tier(0)
    def test_fields_defaults_to_empty_tuple(self) -> None:
        """LogTemplate fields default to empty tuple."""
        template = LogTemplate(
            message="Simple log",
            event_type="simple_event",
        )

        assert template.fields == ()

    @pytest.mark.tra("Events.LogTemplate.Immutability")
    @pytest.mark.tier(0)
    def test_immutability(self) -> None:
        """LogTemplate is immutable after creation."""
        template = LogTemplate(
            message="Order placed",
            event_type="order_placed",
            fields=("order_id",),
        )

        with pytest.raises(AttributeError):
            template.message = "Changed"  # type: ignore[misc]


class TestMetricTemplate:
    """Tests for MetricTemplate dataclass."""

    @pytest.mark.tra("Events.MetricTemplate.Counter")
    @pytest.mark.tier(0)
    def test_counter_creation(self) -> None:
        """MetricTemplate can define a counter metric."""
        template = MetricTemplate(
            name="orders_total",
            metric_type="counter",
            labels=("customer_id",),
        )

        assert template.name == "orders_total"
        assert template.metric_type == "counter"
        assert template.labels == ("customer_id",)
        assert template.value_field is None
        assert template.buckets is None

    @pytest.mark.tra("Events.MetricTemplate.Histogram")
    @pytest.mark.tier(0)
    def test_histogram_with_buckets(self) -> None:
        """MetricTemplate can define a histogram with buckets."""
        template = MetricTemplate(
            name="order_amount_dollars",
            metric_type="histogram",
            value_field="total_amount",
            buckets=(10.0, 50.0, 100.0, 500.0, 1000.0),
        )

        assert template.name == "order_amount_dollars"
        assert template.metric_type == "histogram"
        assert template.value_field == "total_amount"
        assert template.buckets == (10.0, 50.0, 100.0, 500.0, 1000.0)

    @pytest.mark.tra("Events.MetricTemplate.Gauge")
    @pytest.mark.tier(0)
    def test_gauge_with_value_field(self) -> None:
        """MetricTemplate can define a gauge metric."""
        template = MetricTemplate(
            name="queue_depth",
            metric_type="gauge",
            value_field="depth",
        )

        assert template.metric_type == "gauge"
        assert template.value_field == "depth"

    @pytest.mark.tra("Events.MetricTemplate.Defaults")
    @pytest.mark.tier(0)
    def test_labels_defaults_to_empty_tuple(self) -> None:
        """MetricTemplate labels default to empty tuple."""
        template = MetricTemplate(
            name="events_total",
            metric_type="counter",
        )

        assert template.labels == ()

    @pytest.mark.tra("Events.MetricTemplate.Immutability")
    @pytest.mark.tier(0)
    def test_immutability(self) -> None:
        """MetricTemplate is immutable after creation."""
        template = MetricTemplate(
            name="orders_total",
            metric_type="counter",
        )

        with pytest.raises(AttributeError):
            template.name = "changed"  # type: ignore[misc]


class TestEventDescriptor:
    """Tests for EventDescriptor dataclass."""

    @pytest.mark.tra("Events.EventDescriptor.SingleLog")
    @pytest.mark.tier(0)
    def test_single_log_template(self) -> None:
        """EventDescriptor can have a single log template."""
        log_template = LogTemplate(
            message="Order placed",
            event_type="order_placed",
            fields=("order_id", "customer_id"),
        )
        descriptor = EventDescriptor(
            event_class="OrderPlaced",
            log_templates=(log_template,),
        )

        assert descriptor.event_class == "OrderPlaced"
        assert len(descriptor.log_templates) == 1
        assert descriptor.log_templates[0].message == "Order placed"
        assert descriptor.metric_templates == ()

    @pytest.mark.tra("Events.EventDescriptor.SingleMetric")
    @pytest.mark.tier(0)
    def test_single_metric_template(self) -> None:
        """EventDescriptor can have a single metric template."""
        metric_template = MetricTemplate(
            name="orders_total",
            metric_type="counter",
        )
        descriptor = EventDescriptor(
            event_class="OrderPlaced",
            metric_templates=(metric_template,),
        )

        assert descriptor.event_class == "OrderPlaced"
        assert len(descriptor.metric_templates) == 1
        assert descriptor.metric_templates[0].name == "orders_total"
        assert descriptor.log_templates == ()

    @pytest.mark.tra("Events.EventDescriptor.MultipleOutputs")
    @pytest.mark.tier(0)
    def test_multiple_outputs(self) -> None:
        """EventDescriptor can have log and multiple metric templates."""
        log_template = LogTemplate(
            message="Order placed",
            event_type="order_placed",
        )
        counter_template = MetricTemplate(
            name="orders_total",
            metric_type="counter",
        )
        histogram_template = MetricTemplate(
            name="order_amount_dollars",
            metric_type="histogram",
            value_field="total_amount",
            buckets=(10.0, 50.0, 100.0),
        )

        descriptor = EventDescriptor(
            event_class="OrderPlaced",
            log_templates=(log_template,),
            metric_templates=(counter_template, histogram_template),
        )

        assert len(descriptor.log_templates) == 1
        assert len(descriptor.metric_templates) == 2

    @pytest.mark.tra("Events.EventDescriptor.Defaults")
    @pytest.mark.tier(0)
    def test_templates_default_to_empty(self) -> None:
        """EventDescriptor templates default to empty tuples."""
        descriptor = EventDescriptor(event_class="EmptyEvent")

        assert descriptor.log_templates == ()
        assert descriptor.metric_templates == ()

    @pytest.mark.tra("Events.EventDescriptor.Immutability")
    @pytest.mark.tier(0)
    def test_immutability(self) -> None:
        """EventDescriptor is immutable after creation."""
        descriptor = EventDescriptor(event_class="OrderPlaced")

        with pytest.raises(AttributeError):
            descriptor.event_class = "Changed"  # type: ignore[misc]
