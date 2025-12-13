"""Unit tests for instrumentation decorator."""

import time

import pytest

from observabilipy.core.instrument import InstrumentResult, instrument


class TestInstrumentResult:
    """Tests for InstrumentResult dataclass."""

    @pytest.mark.core
    def test_instrument_result_has_value_field(self) -> None:
        """InstrumentResult stores the wrapped function's return value."""
        result = InstrumentResult(value=42)
        assert result.value == 42

    @pytest.mark.core
    def test_instrument_result_has_samples_list(self) -> None:
        """InstrumentResult has empty samples list by default."""
        result = InstrumentResult(value=None)
        assert result.samples == []

    @pytest.mark.core
    def test_instrument_result_has_error_field(self) -> None:
        """InstrumentResult can capture an exception."""
        error = ValueError("test error")
        result = InstrumentResult(value=None, error=error)
        assert result.error is error

    @pytest.mark.core
    def test_instrument_result_error_defaults_to_none(self) -> None:
        """InstrumentResult error is None when no exception occurred."""
        result = InstrumentResult(value="success")
        assert result.error is None

    @pytest.mark.core
    def test_instrument_result_accepts_any_value_type(self) -> None:
        """InstrumentResult value field accepts any type."""
        result_str = InstrumentResult(value="string")
        result_dict = InstrumentResult(value={"key": "value"})
        result_list = InstrumentResult(value=[1, 2, 3])

        assert result_str.value == "string"
        assert result_dict.value == {"key": "value"}
        assert result_list.value == [1, 2, 3]


class TestInstrumentDecorator:
    """Tests for @instrument decorator."""

    @pytest.mark.core
    def test_instrument_returns_instrument_result(self) -> None:
        """Decorated function returns InstrumentResult."""

        @instrument("test_op")
        def my_func() -> int:
            return 42

        result = my_func()
        assert isinstance(result, InstrumentResult)
        assert result.value == 42

    @pytest.mark.core
    def test_instrument_generates_counter_sample(self) -> None:
        """Decorator generates a counter metric sample."""

        @instrument("test_op")
        def my_func() -> str:
            return "done"

        result = my_func()
        counter_samples = [s for s in result.samples if s.name == "test_op_total"]
        assert len(counter_samples) == 1
        assert counter_samples[0].value == 1.0

    @pytest.mark.core
    def test_instrument_counter_has_success_status(self) -> None:
        """Counter sample has status=success on successful execution."""

        @instrument("test_op")
        def my_func() -> str:
            return "done"

        result = my_func()
        counter = next(s for s in result.samples if s.name == "test_op_total")
        assert counter.labels.get("status") == "success"

    @pytest.mark.core
    def test_instrument_preserves_function_arguments(self) -> None:
        """Decorator passes arguments to wrapped function."""

        @instrument("test_op")
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3, 4)
        assert result.value == 7

    @pytest.mark.core
    def test_instrument_generates_histogram_samples(self) -> None:
        """Decorator generates histogram samples for duration."""

        @instrument("test_op")
        def my_func() -> str:
            return "done"

        result = my_func()
        histogram_samples = [s for s in result.samples if "duration_seconds" in s.name]
        # Should have bucket samples + _sum + _count
        assert len(histogram_samples) > 0

    @pytest.mark.core
    def test_instrument_histogram_measures_elapsed_time(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Histogram records elapsed execution time."""
        times = iter([100.0, 100.25])  # 0.25s elapsed
        monkeypatch.setattr(time, "perf_counter", lambda: next(times))

        @instrument("test_op")
        def my_func() -> str:
            return "done"

        result = my_func()
        sum_sample = next(
            s for s in result.samples if s.name == "test_op_duration_seconds_sum"
        )
        assert sum_sample.value == pytest.approx(0.25)

    @pytest.mark.core
    def test_instrument_histogram_has_bucket_samples(self) -> None:
        """Histogram includes bucket samples with le labels."""

        @instrument("test_op")
        def my_func() -> str:
            return "done"

        result = my_func()
        bucket_samples = [
            s for s in result.samples if s.name == "test_op_duration_seconds_bucket"
        ]
        # Default buckets + Inf
        assert len(bucket_samples) > 0
        # All bucket samples should have 'le' label
        assert all("le" in s.labels for s in bucket_samples)

    @pytest.mark.core
    def test_instrument_histogram_has_count_sample(self) -> None:
        """Histogram includes _count sample."""

        @instrument("test_op")
        def my_func() -> str:
            return "done"

        result = my_func()
        count_sample = next(
            s for s in result.samples if s.name == "test_op_duration_seconds_count"
        )
        assert count_sample.value == 1.0

    @pytest.mark.core
    def test_instrument_accepts_static_labels(self) -> None:
        """Labels are attached to all samples."""

        @instrument("test_op", labels={"service": "api", "version": "1.0"})
        def my_func() -> str:
            return "done"

        result = my_func()
        for sample in result.samples:
            assert sample.labels.get("service") == "api"
            assert sample.labels.get("version") == "1.0"

    @pytest.mark.core
    def test_instrument_accepts_custom_buckets(self) -> None:
        """Custom bucket boundaries are used for histogram."""

        @instrument("test_op", buckets=[0.01, 0.1, 1.0])
        def my_func() -> str:
            return "done"

        result = my_func()
        bucket_samples = [
            s for s in result.samples if s.name == "test_op_duration_seconds_bucket"
        ]
        # 3 custom buckets + Inf
        assert len(bucket_samples) == 4
        le_values = {s.labels["le"] for s in bucket_samples}
        assert le_values == {"0.01", "0.1", "1.0", "+Inf"}

    @pytest.mark.core
    def test_instrument_labels_include_status(self) -> None:
        """Status label is added alongside custom labels."""

        @instrument("test_op", labels={"env": "prod"})
        def my_func() -> str:
            return "done"

        result = my_func()
        counter = next(s for s in result.samples if s.name == "test_op_total")
        assert counter.labels.get("env") == "prod"
        assert counter.labels.get("status") == "success"

    @pytest.mark.core
    def test_instrument_captures_exception_in_result(self) -> None:
        """Exception is captured in result.error."""

        @instrument("test_op")
        def my_func() -> str:
            raise ValueError("test error")

        result = my_func()
        assert result.error is not None
        assert isinstance(result.error, ValueError)
        assert str(result.error) == "test error"

    @pytest.mark.core
    def test_instrument_sets_error_status_on_exception(self) -> None:
        """Counter has status=error when function raises."""

        @instrument("test_op")
        def my_func() -> str:
            raise ValueError("test error")

        result = my_func()
        counter = next(s for s in result.samples if s.name == "test_op_total")
        assert counter.labels.get("status") == "error"

    @pytest.mark.core
    def test_instrument_still_records_duration_on_exception(self) -> None:
        """Histogram is recorded even when function raises."""

        @instrument("test_op")
        def my_func() -> str:
            raise ValueError("test error")

        result = my_func()
        histogram_samples = [s for s in result.samples if "duration_seconds" in s.name]
        assert len(histogram_samples) > 0

    @pytest.mark.core
    def test_instrument_value_is_none_on_exception(self) -> None:
        """Result value is None when function raises."""

        @instrument("test_op")
        def my_func() -> str:
            raise ValueError("test error")

        result = my_func()
        assert result.value is None


class TestInstrumentDecoratorAsync:
    """Tests for @instrument decorator with async functions."""

    @pytest.mark.core
    async def test_instrument_works_with_async_functions(self) -> None:
        """Decorated async function returns InstrumentResult."""

        @instrument("test_op")
        async def my_async_func() -> str:
            return "async done"

        result = await my_async_func()
        assert isinstance(result, InstrumentResult)
        assert result.value == "async done"

    @pytest.mark.core
    async def test_instrument_async_generates_counter(self) -> None:
        """Async decorated function generates counter sample."""

        @instrument("test_op")
        async def my_async_func() -> str:
            return "done"

        result = await my_async_func()
        counter_samples = [s for s in result.samples if s.name == "test_op_total"]
        assert len(counter_samples) == 1

    @pytest.mark.core
    async def test_instrument_async_generates_histogram(self) -> None:
        """Async decorated function generates histogram samples."""

        @instrument("test_op")
        async def my_async_func() -> str:
            return "done"

        result = await my_async_func()
        histogram_samples = [s for s in result.samples if "duration_seconds" in s.name]
        assert len(histogram_samples) > 0

    @pytest.mark.core
    async def test_instrument_async_captures_exception(self) -> None:
        """Async decorated function captures exception."""

        @instrument("test_op")
        async def my_async_func() -> str:
            raise ValueError("async error")

        result = await my_async_func()
        assert result.error is not None
        assert isinstance(result.error, ValueError)

    @pytest.mark.core
    async def test_instrument_async_sets_error_status(self) -> None:
        """Async decorated function sets status=error on exception."""

        @instrument("test_op")
        async def my_async_func() -> str:
            raise ValueError("async error")

        result = await my_async_func()
        counter = next(s for s in result.samples if s.name == "test_op_total")
        assert counter.labels.get("status") == "error"

    @pytest.mark.core
    async def test_instrument_async_preserves_arguments(self) -> None:
        """Async decorated function receives arguments."""

        @instrument("test_op")
        async def add(a: int, b: int) -> int:
            return a + b

        result = await add(5, 3)
        assert result.value == 8


class TestPackageExports:
    """Tests for package-level exports."""

    @pytest.mark.core
    def test_instrument_importable_from_package(self) -> None:
        """instrument is importable from observabilipy package."""
        from observabilipy import instrument as pkg_instrument

        assert callable(pkg_instrument)

    @pytest.mark.core
    def test_instrument_result_importable_from_package(self) -> None:
        """InstrumentResult is importable from observabilipy package."""
        from observabilipy import InstrumentResult as PkgResult

        assert PkgResult is not None
