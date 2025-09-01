FROM quay.io/sclorg/python-312-minimal-c9s:latest

LABEL konflux.additional-tags="latest"

# Set working directory (creates /app with default user permissions)
WORKDIR /app

# Install UV package manager
RUN pip install uv

# Copy project files and install dependencies
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY jira_mcp_snowflake /app/jira_mcp_snowflake

# Create virtual environment and install dependencies
RUN uv venv ~/.venv
RUN uv pip install --python ~/.venv/bin/python -e .

# Download Red Hat certificates (optional, may fail outside corporate network)
RUN wget https://certs.corp.redhat.com/certs/Current-IT-Root-CAs.pem -O /tmp/certs.pem 2>/dev/null \
    && cat /tmp/certs.pem >> `~/.venv/bin/python -m certifi` \
    && rm -f /tmp/certs.pem \
    || echo "Red Hat certificate download skipped (not in corporate network)"

# Set Python path to include working directory
ENV PYTHONPATH=/app

# Set default MCP transport if not provided
ENV MCP_TRANSPORT=stdio

# Environment variables (set these when running the container)
# Required:
# SNOWFLAKE_TOKEN - Snowflake authentication token (required)
#
# Optional Configuration:
# SNOWFLAKE_BASE_URL - Snowflake API base URL (optional)
# SNOWFLAKE_ACCOUNT - Snowflake account identifier (optional)
# SNOWFLAKE_DATABASE - Snowflake database name (optional)
# SNOWFLAKE_SCHEMA - Snowflake schema name (optional)
# SNOWFLAKE_WAREHOUSE - Snowflake warehouse name (default: DEFAULT)
# SNOWFLAKE_USER - Snowflake username (optional)
# SNOWFLAKE_PASSWORD - Snowflake password (optional)
# SNOWFLAKE_ROLE - Snowflake role name (optional)
# SNOWFLAKE_CONNECTION_METHOD - Connection method: api or connector (default: api)
# MCP_TRANSPORT - MCP transport type: stdio, http, sse (default: stdio)
# FASTMCP_HOST - FastMCP host address (default: 0.0.0.0)
# FASTMCP_PORT - FastMCP port number (default: 8000)
#
# Performance Tuning:
# ENABLE_CACHING - Enable response caching (default: true)
# CACHE_TTL_SECONDS - Cache time-to-live in seconds (default: 300)
# CACHE_MAX_SIZE - Maximum cache entries (default: 1000)
# MAX_HTTP_CONNECTIONS - HTTP connection pool size (default: 20)
# HTTP_TIMEOUT_SECONDS - HTTP request timeout (default: 60)
# THREAD_POOL_WORKERS - Thread pool size for CPU tasks (default: 10)
# RATE_LIMIT_PER_SECOND - API rate limit per second (default: 50)
# CONCURRENT_QUERY_BATCH_SIZE - Batch size for concurrent queries (default: 5)
#
# Monitoring:
# ENABLE_METRICS - Enable Prometheus metrics (default: false)
# METRICS_PORT - Metrics server port (default: 8000)
#
# Logging:
# PYTHON_LOG_LEVEL - Logging level (default: INFO)

# Expose metrics port and FastMCP port
EXPOSE 8000 8080

# Set entrypoint to run the application using UV virtual environment
CMD ["/opt/app-root/src/.venv/bin/python", "-m", "jira_mcp_snowflake.src.main"]
