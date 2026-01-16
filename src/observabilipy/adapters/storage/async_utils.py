"""Utilities for async-to-sync bridging in storage adapters."""

import asyncio
from collections.abc import AsyncIterable, Coroutine


def _run_sync[T](coro: Coroutine[object, object, T]) -> T:
    """Execute a coroutine synchronously and return its result.

    Creates a new event loop for each call to avoid conflicts with
    existing event loops. This is safe for sync contexts like WSGI.

    Args:
        coro: The coroutine to execute.

    Returns:
        The result of the coroutine.

    Raises:
        Any exception raised by the coroutine.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _collect_async_iterable[T](ait: AsyncIterable[T]) -> list[T]:
    """Collect all items from an async iterable into a list.

    This is useful for sync versions of read() methods that need
    to return a list instead of an AsyncIterable.

    Args:
        ait: The async iterable to collect.

    Returns:
        A list containing all items from the async iterable.
    """

    async def _collect() -> list[T]:
        return [item async for item in ait]

    return _run_sync(_collect())
