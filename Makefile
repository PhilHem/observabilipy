# Makefile for observabilipy
# CI parity: these commands match what CI runs

.PHONY: test test-unit test-events test-bdd test-integration lint lint-fix typecheck format install clean

# Run all tests
test:
	uv run pytest

# Run unit tests only
test-unit:
	uv run pytest tests/unit/

# Run event unit tests
test-events:
	uv run pytest tests/unit/events/ -v

# Run BDD feature tests
test-bdd:
	uv run pytest tests/features/ -v

# Run integration tests only
test-integration:
	uv run pytest tests/integration/

# Run linting
lint:
	uv run ruff check src/ tests/

# Fix linting errors automatically
lint-fix:
	uv run ruff check --fix src/ tests/

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
