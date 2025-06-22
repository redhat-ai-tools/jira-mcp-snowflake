FROM registry.access.redhat.com/ubi9/python-311

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY mcp_server.py ./
COPY config.py ./
COPY database.py ./
COPY tools.py ./
COPY metrics.py ./
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

CMD ["python", "mcp_server.py"]
