FROM registry.access.redhat.com/ubi9/python-311 AS BASE

WORKDIR /app

# Install UV
RUN pip install uv

# Copy project files needed for uv sync
COPY pyproject.toml ./
COPY .python-version ./
COPY README.md ./

# Copy application files (needed for editable install)
COPY ./src/ ./src/

FROM BASE AS LINTER
# tint testing 
RUN uv sync && \
    uv run flake8 src/ --max-line-length=120 --ignore=E501,W503

FROM LINTER AS FINAL
# Install dependencies using UV
RUN uv sync --no-dev
# Environment variables (set these when running the container)
# SNOWFLAKE_BASE_URL - Snowflake API base URL (optional, defaults to Red Hat's instance)
# SNOWFLAKE_TOKEN - Snowflake authentication token (required)
# SNOWFLAKE_DATABASE - Snowflake database name (optional)
# SNOWFLAKE_SCHEMA - Snowflake schema name (optional)
# MCP_TRANSPORT - MCP transport type (optional)

# Set default MCP transport if not provided
ENV MCP_TRANSPORT=stdio

# Expose metrics port
EXPOSE 8000

CMD ["uv", "run", "python", "src/mcp_server.py"]
