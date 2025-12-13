"""Root pytest configuration for conditional module collection.

This conftest.py handles optional dependencies by skipping collection of modules
that import unavailable packages. This allows running tests like `pytest -m core`
without having fastapi installed.
"""

# Modules to skip when fastapi is not installed
_FASTAPI_MODULES = [
    "src/observabilipy/adapters/frameworks/fastapi.py",
    "tests/integration/test_fastapi_example.py",
    "examples/fastapi_example.py",
]

collect_ignore_glob: list[str] = []

try:
    import fastapi  # noqa: F401
except ImportError:
    collect_ignore_glob.extend(_FASTAPI_MODULES)
