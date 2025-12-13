"""Example demonstrating ObservabilipyHandler for Python logging integration.

This example shows how to bridge Python's standard logging module to
observabilipy's log storage system using ObservabilipyHandler.

Run with:
    python examples/logging_handler_example.py

The handler captures:
- Log level, message, and timestamp
- Source information (module, function, line number, file path)
- Extra attributes passed via the `extra` parameter
- Exception info when using logger.exception()
"""

import asyncio
import logging

from observabilipy import InMemoryLogStorage, ObservabilipyHandler


def _run_async(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


async def _collect_entries(storage):
    """Collect all log entries from storage."""
    return [e async for e in storage.read()]


def main() -> None:
    # Create storage and handler
    storage = InMemoryLogStorage()
    handler = ObservabilipyHandler(storage)

    # Configure a logger
    logger = logging.getLogger("myapp")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    print("=== ObservabilipyHandler Example ===\n")

    # Basic logging at different levels
    print("1. Basic logging at different levels:")
    logger.debug("Application starting")
    logger.info("Server listening on port 8000")
    logger.warning("Connection pool running low")
    logger.error("Failed to connect to database")

    entries = _run_async(_collect_entries(storage))
    for entry in entries:
        print(f"   [{entry.level}] {entry.message}")

    print(f"\n   Total entries: {len(entries)}")

    # Logging with extra attributes (structured logging)
    print("\n2. Structured logging with extra attributes:")
    logger.info(
        "User logged in",
        extra={"user_id": 12345, "ip_address": "192.168.1.100", "session_id": "abc123"},
    )
    logger.info(
        "Request completed",
        extra={"method": "GET", "path": "/api/users", "status_code": 200},
    )

    entries = _run_async(_collect_entries(storage))
    for entry in entries[-2:]:  # Last 2 entries
        print(f"   [{entry.level}] {entry.message}")
        standard_attrs = ["module", "funcName", "lineno", "pathname"]
        extras = {
            k: v for k, v in entry.attributes.items() if k not in standard_attrs
        }
        if extras:
            print(f"       extras: {extras}")

    # Exception logging
    print("\n3. Exception logging:")
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.exception("Mathematical error occurred")

    entries = _run_async(_collect_entries(storage))
    exc_entry = entries[-1]
    print(f"   [{exc_entry.level}] {exc_entry.message}")
    print(f"       exc_type: {exc_entry.attributes.get('exc_type')}")
    print(f"       exc_message: {exc_entry.attributes.get('exc_message')}")

    # Child loggers propagate to parent
    print("\n4. Child logger propagation:")
    db_logger = logging.getLogger("myapp.database")
    api_logger = logging.getLogger("myapp.api")

    db_logger.info("Connected to PostgreSQL")
    api_logger.warning("Rate limit approaching for client X")

    entries = _run_async(_collect_entries(storage))
    for entry in entries[-2:]:
        print(f"   [{entry.level}] {entry.message}")
        print(f"       module: {entry.attributes['module']}")

    # Configurable attributes
    print("\n5. Configurable attributes (module and lineno only):")
    minimal_storage = InMemoryLogStorage()
    minimal_handler = ObservabilipyHandler(
        minimal_storage,
        include_attrs=["module", "lineno"],  # Only these two
    )
    minimal_logger = logging.getLogger("minimal")
    minimal_logger.handlers.clear()
    minimal_logger.addHandler(minimal_handler)
    minimal_logger.setLevel(logging.DEBUG)

    minimal_logger.info("Minimal attributes example")

    entries = _run_async(_collect_entries(minimal_storage))
    print(f"   Attributes: {entries[0].attributes}")

    # Summary
    print("\n=== Summary ===")
    total = _run_async(storage.count())
    print(f"Total log entries captured: {total}")
    print("\nAll logs are now available via observabilipy storage!")
    print("In a real app, mount /logs endpoint to expose these via HTTP.")


if __name__ == "__main__":
    main()
