"""Main entry point for the JIRA MCP Snowflake Server."""

import sys

from jira_mcp_snowflake.src.mcp import JiraMCPSnowflakeServer
from jira_mcp_snowflake.src.settings import settings, validate_config
from jira_mcp_snowflake.utils.pylogger import get_python_logger

# Initialize logger
logger = get_python_logger()


def main() -> None:
    """Main entry point for the MCP server.

    Initializes logging, loads configuration, and starts the JIRA MCP Snowflake server.
    """
    try:
        # Validate configuration
        validate_config(settings)
        logger.info("Configuration validation passed")

        # Initialize and run the MCP server
        server = JiraMCPSnowflakeServer()

        logger.info(f"Starting JIRA MCP Snowflake server with {settings.MCP_TRANSPORT} transport")

        # Start metrics server if enabled
        if settings.ENABLE_METRICS:
            from jira_mcp_snowflake.src.metrics import start_metrics_thread
            start_metrics_thread()

        # Run the MCP server with the configured transport
        if settings.MCP_TRANSPORT == "stdio":
            server.mcp.run(transport="stdio")
        else:
            # For HTTP and SSE transports, provide host and port
            server.mcp.run(
                transport=settings.MCP_TRANSPORT,
                host=settings.FASTMCP_HOST,
                port=settings.FASTMCP_PORT
            )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("JIRA MCP Snowflake server shutting down")


if __name__ == "__main__":
    main()
