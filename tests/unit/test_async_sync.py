"""Tests for async-to-sync wrapper utilities."""

from collections.abc import AsyncIterable
from typing import Any

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.tier(1),
    pytest.mark.tra("Adapter.AsyncSync.SyncBridge"),
]


async def async_add(a: int, b: int) -> int:
    """Test coroutine that adds two numbers."""
    return a + b


async def async_generator(items: list[Any]) -> AsyncIterable[Any]:
    """Test async generator that yields items."""
    for item in items:
        yield item


class TestRunSync:
    """Tests for run_sync utility function."""

    def test_run_sync_executes_coroutine_in_new_loop(self) -> None:
        """_run_sync() executes a coroutine synchronously in a new event loop."""
        from observabilipy.adapters.storage.async_utils import _run_sync

        result = _run_sync(async_add(2, 3))

        assert result == 5

    def test_run_sync_returns_coroutine_result(self) -> None:
        """_run_sync() returns the result of the coroutine."""
        from observabilipy.adapters.storage.async_utils import _run_sync

        async def returns_dict() -> dict[str, int]:
            return {"a": 1, "b": 2}

        result = _run_sync(returns_dict())

        assert result == {"a": 1, "b": 2}

    def test_run_sync_propagates_exceptions(self) -> None:
        """_run_sync() propagates exceptions from the coroutine."""
        from observabilipy.adapters.storage.async_utils import _run_sync

        async def raises_error() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            _run_sync(raises_error())


class TestCollectAsyncIterable:
    """Tests for collect_async_iterable utility function."""

    def test_collect_async_iterable_gathers_all_items(self) -> None:
        """_collect_async_iterable() gathers all items from async iterable into list."""
        from observabilipy.adapters.storage.async_utils import _collect_async_iterable

        items = [1, 2, 3]

        result = _collect_async_iterable(async_generator(items))

        assert result == [1, 2, 3]

    def test_collect_async_iterable_empty(self) -> None:
        """_collect_async_iterable() returns empty list for empty generator."""
        from observabilipy.adapters.storage.async_utils import _collect_async_iterable

        result = _collect_async_iterable(async_generator([]))

        assert result == []

    def test_collect_async_iterable_preserves_order(self) -> None:
        """_collect_async_iterable() preserves insertion order."""
        from observabilipy.adapters.storage.async_utils import _collect_async_iterable

        items = ["z", "a", "m", "b"]

        result = _collect_async_iterable(async_generator(items))

        assert result == ["z", "a", "m", "b"]

    def test_collect_async_iterable_handles_complex_types(self) -> None:
        """_collect_async_iterable() works with complex types."""
        from observabilipy.adapters.storage.async_utils import _collect_async_iterable

        items = [{"a": 1}, {"b": 2}]

        result = _collect_async_iterable(async_generator(items))

        assert result == [{"a": 1}, {"b": 2}]
