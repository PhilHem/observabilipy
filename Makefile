# Makefile for observabilipy
# CI parity: these commands match what CI runs

.PHONY: test test-unit test-integration lint typecheck format install clean

# Run all tests
test:
	uv run pytest

# Run unit tests only
test-unit:
	uv run pytest tests/unit/

# Run integration tests only
test-integration:
	uv run pytest tests/integration/

# Run linting
lint:
	uv run ruff check src/ tests/

# Run type checking
typecheck:
	uv run mypy src/observabilipy/

# Format code
format:
	uv run ruff format src/ tests/

# Install dependencies
install:
	uv sync

# Clean build artifacts
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
