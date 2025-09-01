"""Settings for the JIRA MCP Snowflake Server."""

from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

from jira_mcp_snowflake.utils.pylogger import get_python_logger

# Initialize logger
logger = get_python_logger()

# Load environment variables with error handling
try:
    load_dotenv()
except Exception as e:
    # Log error but don't fail - environment variables might be set directly
    logger.warning(f"Could not load .env file: {e}")


class Settings(BaseSettings):
    """Configuration settings for the JIRA MCP Snowflake Server.

    Uses Pydantic BaseSettings to load and validate configuration from environment variables.
    Provides default values for optional settings and validation for required ones.
    """

    # MCP Server Configuration
    MCP_HOST: str = Field(
        default="0.0.0.0",
        json_schema_extra={
            "env": "MCP_HOST",
            "description": "Host address for the MCP server",
            "example": "localhost",
        },
    )
    MCP_PORT: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        json_schema_extra={
            "env": "MCP_PORT",
            "description": "Port number for the MCP server",
            "example": 8080,
        },
    )
    MCP_TRANSPORT: str = Field(
        default="stdio",
        json_schema_extra={
            "env": "MCP_TRANSPORT",
            "description": "Transport protocol for the MCP server",
            "example": "stdio",
            "enum": ["stdio", "http", "sse"],
        },
    )
    FASTMCP_HOST: str = Field(
        default="0.0.0.0",
        json_schema_extra={
            "env": "FASTMCP_HOST",
            "description": "FastMCP host address",
            "example": "localhost",
        },
    )
    FASTMCP_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        json_schema_extra={
            "env": "FASTMCP_PORT",
            "description": "FastMCP port number",
            "example": 8000,
        },
    )

    # Logging Configuration
    PYTHON_LOG_LEVEL: str = Field(
        default="INFO",
        json_schema_extra={
            "env": "PYTHON_LOG_LEVEL",
            "description": "Logging level for the application",
            "example": "INFO",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        },
    )

    # Snowflake Configuration
    SNOWFLAKE_BASE_URL: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_BASE_URL",
            "description": "Snowflake base URL",
            "example": "https://account.snowflakecomputing.com",
        },
    )
    SNOWFLAKE_ACCOUNT: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_ACCOUNT",
            "description": "Snowflake account identifier",
            "example": "xy12345.us-east-1",
        },
    )
    SNOWFLAKE_DATABASE: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_DATABASE",
            "description": "Snowflake database name",
            "example": "JIRA_DB",
        },
    )
    SNOWFLAKE_SCHEMA: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_SCHEMA",
            "description": "Snowflake schema name",
            "example": "PUBLIC",
        },
    )
    SNOWFLAKE_WAREHOUSE: str = Field(
        default="DEFAULT",
        json_schema_extra={
            "env": "SNOWFLAKE_WAREHOUSE",
            "description": "Snowflake warehouse name",
            "example": "COMPUTE_WH",
        },
    )
    SNOWFLAKE_USER: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_USER",
            "description": "Snowflake username",
            "example": "john.doe",
        },
    )
    SNOWFLAKE_PASSWORD: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_PASSWORD",
            "description": "Snowflake password",
            "example": "secretpassword",
            "sensitive": True,
        },
    )
    SNOWFLAKE_ROLE: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_ROLE",
            "description": "Snowflake role name",
            "example": "JIRA_READER",
        },
    )
    SNOWFLAKE_CONNECTION_METHOD: str = Field(
        default="api",
        json_schema_extra={
            "env": "SNOWFLAKE_CONNECTION_METHOD",
            "description": "Connection method: api (REST API) or connector (snowflake.connector)",
            "example": "api",
            "enum": ["api", "connector"],
        },
    )
    SNOWFLAKE_AUTHENTICATOR: str = Field(
        default="snowflake",
        json_schema_extra={
            "env": "SNOWFLAKE_AUTHENTICATOR",
            "description": "Snowflake authenticator type",
            "example": "snowflake",
        },
    )
    SNOWFLAKE_PRIVATE_KEY_FILE: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_PRIVATE_KEY_FILE",
            "description": "Path to Snowflake private key file",
            "example": "/path/to/private_key.pem",
        },
    )
    SNOWFLAKE_PRIVATE_KEY_FILE_PWD: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_PRIVATE_KEY_FILE_PWD",
            "description": "Password for Snowflake private key file",
            "example": "keypassword",
            "sensitive": True,
        },
    )
    SNOWFLAKE_OAUTH_CLIENT_ID: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_OAUTH_CLIENT_ID",
            "description": "Snowflake OAuth client ID",
            "example": "client123",
        },
    )
    SNOWFLAKE_OAUTH_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_OAUTH_CLIENT_SECRET",
            "description": "Snowflake OAuth client secret",
            "example": "secret123",
            "sensitive": True,
        },
    )
    SNOWFLAKE_OAUTH_TOKEN_URL: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_OAUTH_TOKEN_URL",
            "description": "Snowflake OAuth token URL",
            "example": "https://account.snowflakecomputing.com/oauth/token",
        },
    )
    SNOWFLAKE_TOKEN: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "env": "SNOWFLAKE_TOKEN",
            "description": "Snowflake access token",
            "example": "token123",
            "sensitive": True,
        },
    )
    INTERNAL_GATEWAY: bool = Field(
        default=False,
        json_schema_extra={
            "env": "INTERNAL_GATEWAY",
            "description": "Whether to use internal gateway",
            "example": False,
        },
    )

    # Metrics Configuration
    ENABLE_METRICS: bool = Field(
        default=False,
        json_schema_extra={
            "env": "ENABLE_METRICS",
            "description": "Enable Prometheus metrics",
            "example": True,
        },
    )
    METRICS_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        json_schema_extra={
            "env": "METRICS_PORT",
            "description": "Port for Prometheus metrics server",
            "example": 8000,
        },
    )

    # Performance Configuration
    ENABLE_CACHING: bool = Field(
        default=True,
        json_schema_extra={
            "env": "ENABLE_CACHING",
            "description": "Enable response caching",
            "example": True,
        },
    )
    CACHE_TTL_SECONDS: int = Field(
        default=300,
        ge=1,
        json_schema_extra={
            "env": "CACHE_TTL_SECONDS",
            "description": "Cache time-to-live in seconds",
            "example": 300,
        },
    )
    CACHE_MAX_SIZE: int = Field(
        default=1000,
        ge=1,
        json_schema_extra={
            "env": "CACHE_MAX_SIZE",
            "description": "Maximum cache size",
            "example": 1000,
        },
    )
    MAX_HTTP_CONNECTIONS: int = Field(
        default=20,
        ge=1,
        le=100,
        json_schema_extra={
            "env": "MAX_HTTP_CONNECTIONS",
            "description": "Maximum HTTP connections",
            "example": 20,
        },
    )
    HTTP_TIMEOUT_SECONDS: int = Field(
        default=60,
        ge=1,
        json_schema_extra={
            "env": "HTTP_TIMEOUT_SECONDS",
            "description": "HTTP timeout in seconds",
            "example": 60,
        },
    )
    THREAD_POOL_WORKERS: int = Field(
        default=10,
        ge=1,
        le=50,
        json_schema_extra={
            "env": "THREAD_POOL_WORKERS",
            "description": "Number of thread pool workers",
            "example": 10,
        },
    )
    RATE_LIMIT_PER_SECOND: int = Field(
        default=50,
        ge=1,
        json_schema_extra={
            "env": "RATE_LIMIT_PER_SECOND",
            "description": "Rate limit per second",
            "example": 50,
        },
    )
    CONCURRENT_QUERY_BATCH_SIZE: int = Field(
        default=5,
        ge=1,
        le=20,
        json_schema_extra={
            "env": "CONCURRENT_QUERY_BATCH_SIZE",
            "description": "Concurrent query batch size",
            "example": 5,
        },
    )


def validate_config(settings: Settings) -> None:
    """Validate configuration settings.

    Performs validation to ensure required settings are present and values
    are within acceptable ranges.

    Args:
        settings: Settings instance to validate.

    Raises:
        ValueError: If required configuration is missing or invalid.
    """
    # Validate port range
    if not (1024 <= settings.MCP_PORT <= 65535):
        raise ValueError(
            f"MCP_PORT must be between 1024 and 65535, got {settings.MCP_PORT}"
        )

    if not (1024 <= settings.FASTMCP_PORT <= 65535):
        raise ValueError(
            f"FASTMCP_PORT must be between 1024 and 65535, got {settings.FASTMCP_PORT}"
        )

    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.PYTHON_LOG_LEVEL.upper() not in valid_log_levels:
        raise ValueError(
            f"PYTHON_LOG_LEVEL must be one of {valid_log_levels}, got {settings.PYTHON_LOG_LEVEL}"
        )

    # Validate transport protocol
    valid_transport_protocols = ["stdio", "http", "sse"]
    if settings.MCP_TRANSPORT not in valid_transport_protocols:
        raise ValueError(
            f"MCP_TRANSPORT must be one of {valid_transport_protocols}, got {settings.MCP_TRANSPORT}"
        )

    # Validate connection method
    valid_connection_methods = ["api", "connector"]
    if settings.SNOWFLAKE_CONNECTION_METHOD not in valid_connection_methods:
        raise ValueError(
            f"SNOWFLAKE_CONNECTION_METHOD must be one of {valid_connection_methods}, got {settings.SNOWFLAKE_CONNECTION_METHOD}"
        )


# Create config instance without validation (validation happens in main.py)
settings = Settings()
