import os
import logging

# Configure logging to stderr so it doesn't interfere with MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# MCP Configuration
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")

# Snowflake API configuration from environment variables
SNOWFLAKE_BASE_URL = os.environ.get("SNOWFLAKE_BASE_URL")
SNOWFLAKE_DATABASE = os.environ.get("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.environ.get("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "DEFAULT")
INTERNAL_GATEWAY = os.environ.get("INTERNAL_GATEWAY", "false")

# Snowflake token handling - for stdio transport or internal gateway, get from environment
# For other transports, it will be retrieved from request context in tools layer
if MCP_TRANSPORT == "stdio" or INTERNAL_GATEWAY.lower() == "true":
    SNOWFLAKE_TOKEN = os.environ.get("SNOWFLAKE_TOKEN")
else:
    # For non-stdio transports, token will be passed from tools layer
    SNOWFLAKE_TOKEN = None

# Prometheus metrics configuration
ENABLE_METRICS = os.environ.get("ENABLE_METRICS", "false").lower() == "true"
METRICS_PORT = int(os.environ.get("METRICS_PORT", "8000"))

# Check if Prometheus is available
try:
    # These imports are used in metrics.py
    from prometheus_client import Counter, Histogram, Gauge, CONTENT_TYPE_LATEST, generate_latest  # noqa: F401
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
