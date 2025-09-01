# note: on MacOS you need to install make via brew ( min version 4.0+)
# brew install make
.ONESHELL:

SHELL			= /bin/bash
CONTAINER_NAME	= "localhost/jira-mcp-snowflake:latest"

# Development dependencies
uv_sync_dev:
	uv sync --dev

# Test target
test: lint pytest

# Build container
build:
	podman build -t $(CONTAINER_NAME) .

# Linting with ruff (replaces flake8)
lint: uv_sync_dev
	uv run ruff check jira_mcp_snowflake/ tests/

# Format code with ruff
format: uv_sync_dev
	uv run ruff format jira_mcp_snowflake/ tests/

# Type checking with mypy
typecheck: uv_sync_dev
	uv run mypy jira_mcp_snowflake/

# Run tests with pytest
pytest: uv_sync_dev
	uv run pytest tests/test_jira_tools.py tests/test_settings.py tests/test_mcp_init.py tests/test_main.py tests/test_api.py tests/test_metrics_comprehensive.py tests/test_database_focused.py --cov=jira_mcp_snowflake --cov-report=xml --cov-report=term -v --tb=short

# Run all quality checks
quality: lint typecheck pytest

# Install pre-commit hooks
install-hooks: uv_sync_dev
	uv run pre-commit install

# Run pre-commit on all files
pre-commit: uv_sync_dev
	uv run pre-commit run --all-files

# Clean up build artifacts
clean:
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -f coverage.xml
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Start the MCP server locally
run: uv_sync_dev
	uv run jira-mcp-snowflake

# Show help
help:
	@echo "Available targets:"
	@echo "  uv_sync_dev   - Install development dependencies"
	@echo "  test          - Run linting and tests"
	@echo "  build         - Build container image"
	@echo "  lint          - Run ruff linting"
	@echo "  format        - Format code with ruff"
	@echo "  typecheck     - Run mypy type checking"
	@echo "  pytest        - Run pytest with coverage"
	@echo "  quality       - Run all quality checks"
	@echo "  install-hooks - Install pre-commit hooks"
	@echo "  pre-commit    - Run pre-commit on all files"
	@echo "  clean         - Clean up build artifacts"
	@echo "  run           - Start the MCP server locally"
	@echo "  help          - Show this help message"

.PHONY: uv_sync_dev test build lint format typecheck pytest quality install-hooks pre-commit clean run help

