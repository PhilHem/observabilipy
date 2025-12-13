"""Contextvars-based logging context helper for ObservabilipyHandler.

This module provides a simple way to attach structured context (like request IDs,
user IDs, correlation IDs) to all logs within a scope without passing `extra={}`
to every logging call.

Example:
    ```python
    from observabilipy import ObservabilipyHandler, InMemoryLogStorage
    from observabilipy import get_log_context, log_context
    import logging

    storage = InMemoryLogStorage()
    handler = ObservabilipyHandler(storage, context_provider=get_log_context)
    logger = logging.getLogger("myapp")
    logger.addHandler(handler)

    with log_context(request_id="req-123", user_id=42):
        logger.info("Processing")  # includes request_id, user_id

    logger.info("Outside")  # no request_id, user_id
    ```
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

# Type for scalar log attributes (matches LogEntry.attributes value type)
LogAttribute = str | int | float | bool

# ContextVar storing the current context dict
# Using contextvars ensures isolation per asyncio task and per thread
# Note: We use a factory pattern via get() with fallback instead of mutable default
_log_context: ContextVar[dict[str, LogAttribute] | None] = ContextVar(
    "observabilipy_log_context", default=None
)


def get_log_context() -> dict[str, LogAttribute]:
    """Return a copy of the current log context.

    Use this as the `context_provider` argument to ObservabilipyHandler.

    Returns:
        A copy of the current context dict. Modifications to the returned
        dict do not affect the stored context.

    Example:
        >>> set_log_context(request_id="abc", user_id=1)
        >>> get_log_context()
        {'request_id': 'abc', 'user_id': 1}
        >>> clear_log_context()
    """
    ctx = _log_context.get()
    if ctx is None:
        return {}
    return ctx.copy()


def set_log_context(**attrs: LogAttribute) -> None:
    """Replace the current log context with new attributes.

    This replaces the entire context. To merge attributes into the existing
    context, use `update_log_context()` instead.

    Args:
        **attrs: Keyword arguments become the new context attributes.

    Example:
        >>> set_log_context(request_id="abc", user_id=1)
        >>> get_log_context()
        {'request_id': 'abc', 'user_id': 1}
        >>> set_log_context(trace_id="xyz")  # Replaces, doesn't merge
        >>> get_log_context()
        {'trace_id': 'xyz'}
        >>> clear_log_context()
    """
    _log_context.set(dict(attrs))


def update_log_context(**attrs: LogAttribute) -> None:
    """Merge attributes into the current log context.

    Existing keys are overwritten if provided again.

    Args:
        **attrs: Keyword arguments to merge into the current context.

    Example:
        >>> set_log_context(request_id="abc")
        >>> update_log_context(user_id=42)
        >>> get_log_context()
        {'request_id': 'abc', 'user_id': 42}
        >>> clear_log_context()
    """
    current = _log_context.get() or {}
    _log_context.set({**current, **attrs})


def clear_log_context() -> None:
    """Clear all attributes from the current log context.

    Example:
        >>> set_log_context(foo="bar")
        >>> clear_log_context()
        >>> get_log_context()
        {}
    """
    _log_context.set(None)


@contextmanager
def log_context(**attrs: LogAttribute) -> Generator[None]:
    """Context manager that adds attributes for the duration of the block.

    Automatically restores the previous context on exit, even if an exception
    is raised. Nested contexts are supported.

    Args:
        **attrs: Keyword arguments to add to the context for the duration
            of the block.

    Example:
        >>> with log_context(request_id="abc123", user_id=42):
        ...     ctx = get_log_context()
        >>> ctx["request_id"]
        'abc123'
        >>> get_log_context()  # Restored after block
        {}
    """
    current = _log_context.get() or {}
    token = _log_context.set({**current, **attrs})
    try:
        yield
    finally:
        _log_context.reset(token)
